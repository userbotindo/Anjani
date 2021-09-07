"""Spam Prediction plugin"""
# Copyright (C) 2020 - 2021  UserbotIndo Team, <https://github.com/userbotindo.git>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
import pickle
import re
from hashlib import sha256
from typing import ClassVar, List, Optional

from pyrogram import filters
from pyrogram.errors import PeerIdInvalid
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

try:
    from sklearn.pipeline import Pipeline

    _run_predict = True
except ImportError:
    from anjani.util.types import Pipeline

    _run_predict = False


from anjani import command, listener, plugin, util
from anjani.filters import staff_only
from anjani.util import run_sync
from anjani.util.types import NDArray


class SpamPrediction(plugin.Plugin):
    name: ClassVar[str] = "SpamPredict"
    disabled: ClassVar[bool] = not _run_predict

    db: util.db.AsyncCollection
    model: Pipeline

    async def on_load(self) -> None:
        token = self.bot.config.get("sp_token")
        url = self.bot.config.get("sp_url")
        if not (token and url):
            self.bot.unload_plugin(self)
            return

        self.db = self.bot.db.get_collection("SPAM_DUMP")
        self.user_db = self.bot.db.get_collection("USERS")
        await self.__load_model(token, url)

    async def __load_model(self, token: str, url: str) -> None:
        self.log.info("Downloading spam prediction model!")
        async with self.bot.http.get(
            url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3.raw",
            },
        ) as res:
            if res.status == 200:
                self.model = await run_sync(pickle.loads, await res.read())
            else:
                self.model = None  # type: ignore
                self.log.warning("Failed to download prediction model!")
                self.bot.unload_plugin(self)

    @staticmethod
    def _build_hash(content: str) -> str:
        return sha256(content.strip().encode()).hexdigest()

    @staticmethod
    def _build_hex(user_id: Optional[int]) -> str:
        return f"{user_id:#x}" if user_id else ""

    @staticmethod
    def prob_to_string(value: float) -> str:
        return str(value * 10 ** 2)[0:7]

    def _predict(self, text: str) -> NDArray[float]:
        return self.model.predict_proba([text])

    def _is_spam(self, text: str) -> Optional[bool]:
        return self.model.predict([text])[0] == "spam"

    @listener.filters(filters.regex(r"spam_check_(t|f)"))
    async def on_callback_query(self, query: CallbackQuery) -> None:
        method = query.matches[0].group(1)
        message = query.message
        content = re.compile(r"([A-Fa-f0-9]{64})").search(message.text)
        author = query.from_user.id

        if not content:
            self.log.warning("Can't get hash from 'MessageID: %d'", message.message_id)
            return

        content_hash = content[0]

        if message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup):
            data = await self.db.find_one({"hash": content_hash})
            if not data:
                await query.answer("The voting poll for this message has ended!")
                return
            users_on_correct = data["spam"]
            users_on_incorrect = data["ham"]
            if method == "t":
                # Check user in incorrect data
                if author in users_on_incorrect:
                    await self.db.update_one({"_id": content_hash}, {"$pull": {"ham": author}})
                    users_on_incorrect.remove(author)
                if author in users_on_correct:
                    await self.db.update_one({"_id": content_hash}, {"$pull": {"spam": author}})
                    users_on_correct.remove(author)
                else:
                    await self.db.update_one({"_id": content_hash}, {"$addToSet": {"spam": author}})
                    users_on_correct.append(author)
            elif method == "f":
                # Check user in correct data
                if author in users_on_correct:
                    await self.db.update_one({"_id": content_hash}, {"$pull": {"spam": author}})
                    users_on_correct.remove(author)
                if author in users_on_incorrect:
                    await self.db.update_one({"_id": content_hash}, {"$pull": {"ham": author}})
                    users_on_incorrect.remove(author)
                else:
                    await self.db.update_one({"_id": content_hash}, {"$addToSet": {"ham": author}})
                    users_on_incorrect.append(author)
            else:
                raise ValueError("Unknown method")
        else:
            return

        total_correct, total_incorrect = len(users_on_correct), len(users_on_incorrect)
        button = [
            [
                InlineKeyboardButton(
                    text=f"✅ Correct ({total_correct})",
                    callback_data="spam_check_t",
                ),
                InlineKeyboardButton(
                    text=f"❌ Incorrect ({total_incorrect})",
                    callback_data="spam_check_f",
                ),
            ],
        ]
        old_btn = query.message.reply_markup.inline_keyboard
        if len(old_btn) > 1:
            button.append(old_btn[1])

        await asyncio.gather(
            query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(button)),
            query.answer(),
        )

    @listener.filters(filters.group)
    async def on_message(self, message: Message) -> None:
        """Checker service for message"""
        chat = message.chat
        user = message.from_user
        text = (
            message.text.strip()
            if message.text
            else (message.caption.strip() if message.media and message.caption else None)
        )
        if not chat or message.left_chat_member or not user or not text:
            return

        # Always check the spam probability but run it in the background
        self.bot.loop.create_task(self.spam_check(message, text))

    async def spam_check(self, message: Message, text: str) -> None:
        if not self.model:
            return

        user = message.from_user.id

        response = await run_sync(self._predict, text.strip())
        if response.size == 0:
            return

        probability = response[0][1]
        if probability <= 0.5:
            return

        content_hash = self._build_hash(text)

        data = await self.db.find_one({"_id": content_hash})
        if not data:
            await self.db.insert_one(
                {"_id": content_hash, "hash": content_hash, "text": text, "spam": [], "ham": []}
            )

        identifier = self._build_hex(user)
        proba_str = self.prob_to_string(probability)

        msg = (
            "#SPAM_PREDICTION\n\n"
            f"**Prediction Result**: {proba_str}\n"
            f"**Identifier:** `{identifier}`\n"
            f"**Message Hash:** `{content_hash}`\n"
            f"\n**====== CONTENT =======**\n\n{text}"
        )

        keyb = [
            [
                InlineKeyboardButton(text="✅ Correct (0)", callback_data="spam_check_t"),
                InlineKeyboardButton(text="❌ Incorrect (0)", callback_data="spam_check_f"),
            ]
        ]

        if message.chat.username:
            keyb.append(
                [InlineKeyboardButton(text="Chat", url=f"https://t.me/{message.chat.username}")]
            )
        if message.forward_from_chat and message.forward_from_chat.username:
            raw_btn = InlineKeyboardButton(
                text="Channel", url=f"https://t.me/{message.forward_from_chat.username}"
            )
            if message.chat.username:
                keyb[1].append(raw_btn)
            else:
                keyb.append([raw_btn])

        msg = await self.bot.client.send_message(
            chat_id=-1001314588569,
            text=msg,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(keyb),
        )
        if probability >= 0.9:
            await message.reply_text(
                f"❗️**SPAM ALERT**❗️\n"
                f"**ID:** `{identifier}`\n"
                f"**Message Hash:** `{content_hash}`\n"
                f"**Spam Probability:** {proba_str}%",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("View Message", url=msg.link)]]
                ),
            )

    @command.filters(staff_only)
    async def cmd_update_model(self, _: command.Context) -> str:
        token = self.bot.config.get("sp_token")
        url = self.bot.config.get("sp_url")
        if not (token and url):
            return "No token provided!"

        await self.__load_model(token, url)
        return "Done"

    @command.filters(staff_only)
    async def cmd_spam(self, ctx: command.Context) -> Optional[str]:
        """Manual spam detection by bot staff"""
        user_id = None
        if ctx.msg.reply_to_message:
            content = ctx.msg.reply_to_message.text or ctx.msg.reply_to_message.caption
            if ctx.msg.reply_to_message.from_user.id != ctx.author.id:
                user_id = ctx.msg.reply_to_message.from_user.id
        else:
            content = ctx.input
            if not content:
                return "Give me a text or reply to a message / forwarded message"

        identifier = self._build_hex(user_id)

        content_hash = self._build_hash(content)
        pred = await run_sync(self._predict, content.strip())
        if pred.size == 0:
            return "Prediction failed"

        proba = pred[0][1]
        text = f"#SPAM\n\n**CPU Prediction:** `{self.prob_to_string(proba)}`\n"
        if identifier:
            text += f"**Identifier:** {identifier}\n"

        text += f"**Message Hash:** `{content_hash}`\n\n**======= CONTENT =======**\n\n{content}"
        _, msg = await asyncio.gather(
            self.db.update_one(
                {"_id": content_hash},
                {
                    "$set": {
                        "text": content.strip(),
                        "spam": 1,
                        "ham": 0,
                    }
                },
                upsert=True,
            ),
            self.bot.client.send_message(
                chat_id=-1001314588569,
                text=text,
                disable_web_page_preview=True,
            ),
        )
        await ctx.respond(
            "Message logged as spam!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("View Message", url=msg.link)]]
            ),
        )
        return None

    @command.filters(staff_only, aliases=["prediction"])
    async def cmd_predict(self, ctx: command.Context) -> Optional[str]:
        """Look a prediction for a replied message"""
        replied = ctx.msg.reply_to_message
        if not replied:
            await ctx.respond("Reply to a message!", delete_after=5)
            return None

        content = replied.text or replied.caption
        pred = await util.run_sync(self._predict, content)
        is_spam = await util.run_sync(self._is_spam, content)
        if pred.size == 0:
            return "Prediction failed"

        return (
            "**Result**\n\n"
            f"**Is Spam:** {is_spam}\n"
            f"**Spam Prediction:** `{self.prob_to_string(pred[0][1])}`\n"
            f"**Ham Prediction:** `{self.prob_to_string(pred[0][0])}`"
        )

    @command.filters(aliases=["spaminfo"])
    async def cmd_sinfo(self, ctx: command.Context, *, arg: str = "") -> Optional[str]:
        """Get information fro spam identifier"""
        res = re.search(r"(0x[\da-f]+)", arg, re.IGNORECASE)
        if not res:
            return "Can't find any identifier"

        user_id = int(res.group(0), 0)
        user_data = await self.user_db.find_one({"_id": user_id})
        if not user_data:
            return "Looks like I don't have control over that user, or the ID isn't a valid one."

        text = (
            f"**Private ID:** `{res.group(0)}`\n\n"
            "**User Info**\n\n"
            f"**User ID:** `{user_id}`\n"
        )
        try:
            user = await ctx.bot.client.get_users(user_id)
            if isinstance(user, List):
                user = user[0]
            text += f"**First Name:** {user.first_name}\n"
            if user.last_name:
                text += f"**Last Name:** {user.last_name}\n"
            text += f"**Username:** @{user.username}\n"
            text += f"**Reputation:** {user_data['reputation']}\n"
            text += f"**User Link:** {user.mention}"
        except PeerIdInvalid:
            text += f"**Username:** @{user_data['username']}\n"
            text += f"**Reputation:** {user_data['reputation']}\n"
            text += f"**User Link:** tg://user?id={user_id}"

        return text
