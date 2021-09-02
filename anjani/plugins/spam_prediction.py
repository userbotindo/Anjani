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
from pyrogram.errors import ChannelPrivate
from pyrogram.types import (
    CallbackQuery,
    Chat,
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

    def _build_hash(self, content: str) -> str:
        return sha256(content.strip().encode()).hexdigest()

    def _build_hex(self, user_id: Optional[int] = None, chat_id: Optional[int] = None) -> str:
        if not user_id:
            return ""

        if not chat_id or user_id == chat_id:
            return f"{user_id:#x}"

        return f"{user_id:#x}{chat_id:x}"

    def _predict(self, text: str) -> NDArray[float]:
        return self.model.predict_proba([text])

    def _is_spam(self, text: str) -> Optional[bool]:
        return True if self.model.predict([text])[0] == "spam" else False

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
        button = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=f"✅ Correct ({total_correct})",
                        callback_data=f"spam_check_t",
                    ),
                    InlineKeyboardButton(
                        text=f"❌ Incorrect ({total_incorrect})",
                        callback_data=f"spam_check_f",
                    ),
                ]
            ]
        )

        await asyncio.gather(query.edit_message_reply_markup(reply_markup=button), query.answer())

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
        self.bot.loop.create_task(self.spam_check(chat.id, message.from_user.id, text))

    async def spam_check(self, chat: int, user: int, text: str) -> None:
        response = await run_sync(self._predict, text.strip())
        if response.size == 0:
            return

        probability = response[0][1]
        if probability <= 0.5:
            return

        content_hash = self._build_hash(text)

        data = await self.db.find_one({"_id": content_hash})
        if data:
            return

        msg = (
            "#SPAM_PREDICTION\n\n"
            f"**Prediction Result**: {str(probability * 10 ** 2)[0:7]}\n"
            f"**Identifier:** `{self._build_hex(user_id=user, chat_id=chat)}`\n"
            f"**Message Hash:** `{content_hash}`\n"
            f"\n**====== CONTENT =======**\n\n{text}"
        )
        await asyncio.gather(
            self.bot.client.send_message(
                chat_id=-1001314588569,
                text=msg,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="✅ Correct (0)",
                                callback_data=f"spam_check_t",
                            ),
                            InlineKeyboardButton(
                                text="❌ Incorrect (0)",
                                callback_data=f"spam_check_f",
                            ),
                        ]
                    ]
                ),
            ),
            self.db.insert_one(
                {"_id": content_hash, "hash": content_hash, "text": text, "spam": [], "ham": []}
            ),
        )

    @command.filters(staff_only)
    async def cmd_spam(self, ctx: command.Context) -> Optional[str]:
        """Manual spam detection by bot staff"""
        if ctx.msg.reply_to_message:
            content = ctx.msg.reply_to_message.text or ctx.msg.reply_to_message.caption
            user_id = ctx.msg.reply_to_message.from_user.id
            chat_id = ctx.chat.id if ctx.chat.type != "private" else None
        else:
            user_id = chat_id = None
            content = ctx.input
            if not content:
                return "Give me a text or reply to a message / forwarded message"

        identifier = self._build_hex(user_id=user_id, chat_id=chat_id)

        content_hash = self._build_hash(content)
        pred = await run_sync(self._predict, content.strip())
        if pred.size == 0:
            return "Prediction failed"

        proba = pred[0][1]
        text = f"#SPAM\n\n**CPU Prediction:** `{str(proba * 10 ** 2)[0:7]}`\n"
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
            f"**Spam Prediction:** `{str(pred[0][1] * 10 ** 2)[0:7]}`\n"
            f"**Ham Prediction:** `{str(pred[0][0] * 10 ** 2)[0:7]}`"
        )

    @command.filters(aliases=["spaminfo"])
    async def cmd_sinfo(self, ctx: command.Context, *, arg: str = "") -> Optional[str]:
        """Get information fro spam identifier"""
        res = re.search(r"(0x[\da-f]+)(-[\da-f]+)?", arg, re.IGNORECASE)
        if not res:
            return "Can't find any identifier"

        user = await self.bot.client.get_users(int(res.group(1), 0))
        if isinstance(user, List):
            user = user[0]

        text = (
            f"**Private ID: **`{res.group(0)}`\n\n"
            "**User Info**\n\n"
            f"**User ID: **`{user.id}`\n"
            f"**First Name: **{user.first_name}\n"
        )
        if user.last_name:
            text += f"**Last Name: **{user.last_name}\n"
        text += f"**Username: **@{user.username}\n"
        text += f"**User Link: **{user.mention}\n"

        if res.group(2):
            try:
                chat = await self.bot.client.get_chat(int(res.group(2), 16))
                if not isinstance(chat, Chat):
                    return "Invalid Chat type"

                text += "\n**Chat Info**\n\n"
                text += f"**Chat ID:** `{chat.id}`\n"
                text += f"**Chat Type :** {chat.type}\n"
                text += f"**Chat Title :** {chat.title}\n"
                if chat.username:
                    text += f"**Chat Username :** @{chat.username}\n"
            except ChannelPrivate:
                pass

        await ctx.respond(text)
        return None
