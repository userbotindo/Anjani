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
from hashlib import md5, sha256
from typing import Any, ClassVar, MutableMapping, Optional

from pymongo.errors import DuplicateKeyError
from pyrogram.errors import (
    ChatAdminRequired,
    FloodWait,
    MessageDeleteForbidden,
    MessageNotModified,
    QueryIdInvalid,
    UserAdminInvalid,
)
from pyrogram.errors.exceptions.bad_request_400 import MessageIdInvalid
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

from anjani import command, filters, listener, plugin, util


class SpamPrediction(plugin.Plugin):
    name: ClassVar[str] = "SpamPredict"
    helpable: ClassVar[bool] = True
    disabled: ClassVar[bool] = not _run_predict

    db: util.db.AsyncCollection
    user_db: util.db.AsyncCollection
    setting_db: util.db.AsyncCollection
    model: Pipeline

    async def on_load(self) -> None:
        token = self.bot.config.get("sp_token")
        url = self.bot.config.get("sp_url")
        if not (token and url):
            return self.bot.unload_plugin(self)

        self.db = self.bot.db.get_collection("SPAM_DUMP")
        self.user_db = self.bot.db.get_collection("USERS")
        self.setting_db = self.bot.db.get_collection("SPAM_PREDICT_SETTING")
        await self.__load_model(token, url)

    async def on_chat_migrate(self, message: Message) -> None:
        await self.db.update_one(
            {"chat_id": message.migrate_from_chat_id},
            {"$set": {"chat_id": message.chat.id}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        setting = await self.setting_db.find_one({"chat_id": chat_id})
        return {self.name: setting} if setting else {}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.setting_db.update_one(
            {"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True
        )

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
                self.model = await util.run_sync(pickle.loads, await res.read())
            else:
                self.log.warning("Failed to download prediction model!")
                self.bot.unload_plugin(self)

    @staticmethod
    def _build_hash(content: str) -> str:
        return sha256(content.strip().encode()).hexdigest()

    def _build_hex(self, id: Optional[int]) -> str:
        return md5((str(id) + self.bot.user.username).encode()).hexdigest()  # skipcq: PTC-W1003

    @staticmethod
    def prob_to_string(value: float) -> str:
        return str(value * 10 ** 2)[0:7]

    async def _predict(self, text: str) -> util.types.NDArray[float]:
        return await util.run_sync(self.model.predict_proba, [text])

    async def _is_spam(self, text: str) -> bool:
        return (await util.run_sync(self.model.predict, [text]))[0] == "spam"

    @listener.filters(filters.regex(r"spam_check_(t|f)"))
    async def on_callback_query(self, query: CallbackQuery) -> None:
        method = query.matches[0].group(1)
        message = query.message
        content = re.compile(r"([A-Fa-f0-9]{64})").search(message.text)
        author = query.from_user.id

        if not content:
            return self.log.warning("Can't get hash from 'MessageID: %d'", message.message_id)

        content_hash = content[0]

        if message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup):
            data = await self.db.find_one({"_id": content_hash})
            if not data:
                return await query.answer("The voting poll for this message has ended!")

            users_on_correct = data["spam"]
            users_on_incorrect = data["ham"]
            if method == "t":
                try:
                    # Check user in incorrect data
                    if author in users_on_incorrect:
                        users_on_incorrect.remove(author)
                    if author in users_on_correct:
                        users_on_correct.remove(author)
                    else:
                        users_on_correct.append(author)
                except TypeError:
                    return await query.answer(
                        "You can't vote this anymore, because this was marked as a spam by our staff",
                        show_alert=True,
                    )
            elif method == "f":
                try:
                    # Check user in correct data
                    if author in users_on_correct:
                        users_on_correct.remove(author)
                    if author in users_on_incorrect:
                        users_on_incorrect.remove(author)
                    else:
                        users_on_incorrect.append(author)
                except TypeError:
                    return await query.answer(
                        "You can't vote this anymore, because this was marked as a spam by our staff",
                        show_alert=True,
                    )
            else:
                raise ValueError("Unknown method")
        else:
            return

        await self.db.update_one(
            {"_id": content_hash}, {"$set": {"spam": users_on_correct, "ham": users_on_incorrect}}
        )

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

        if isinstance(query.message.reply_markup, InlineKeyboardMarkup):
            old_btn = query.message.reply_markup.inline_keyboard
            if len(old_btn) > 1:
                button.append(old_btn[1])

        for i in data["msg_id"]:
            try:
                while True:
                    try:
                        await self.bot.client.edit_message_reply_markup(
                            -1001314588569, i, InlineKeyboardMarkup(button)
                        )
                    except MessageIdInvalid:
                        pass
                    except MessageNotModified:
                        await query.answer(
                            "You already voted this content, "
                            "this happened because there are multiple same of contents exists.",
                            show_alert=True,
                        )
                    except FloodWait as flood:
                        await query.answer(
                            f"Please wait i'm updating the content for you.",
                            show_alert=True,
                        )
                        await asyncio.sleep(flood.x)  # type: ignore
                        continue

                    await asyncio.sleep(0.1)
                    break
            except QueryIdInvalid:
                self.log.debug("Can't edit message, invalid query id '%s'", query.id)
                continue

        try:
            await query.answer()
        except QueryIdInvalid:
            pass

    @listener.filters(filters.group)
    async def on_message(self, message: Message) -> None:
        """Checker service for message"""
        setting = await self.setting_db.find_one({"chat_id": message.chat.id})
        if setting and not setting.get("setting"):
            return

        chat = message.chat
        user = message.from_user
        text = (
            message.text.strip()
            if message.text
            else (message.caption.strip() if message.media and message.caption else None)
        )
        if not chat or message.left_chat_member or not user or not text:
            return

        # Always check the spam probability
        await self.spam_check(message, text)

    async def spam_check(self, message: Message, text: str) -> None:
        user = message.from_user.id

        response = await self._predict(text.strip())
        if response.size == 0:
            return

        probability = response[0][1]
        if probability <= 0.5:
            return

        content_hash = self._build_hash(text)
        identifier = self._build_hex(user)
        proba_str = self.prob_to_string(probability)

        notice = (
            "#SPAM_PREDICTION\n\n"
            f"**Prediction Result**: {proba_str}\n"
            f"**Identifier:** `{identifier}`\n"
        )
        if ch := message.forward_from_chat:
            notice += f"**Channel ID:** `{self._build_hex(ch.id)}`\n"
        notice += f"**Message Hash:** `{content_hash}`\n\n**====== CONTENT =======**\n\n{text}"

        l_spam, l_ham = 0, 0
        _, data = await asyncio.gather(
            self.bot.log_stat("predicted"), self.db.find_one({"_id": content_hash})
        )
        if data:
            l_spam = len(data["spam"])
            l_ham = len(data["ham"])

        keyb = [
            [
                InlineKeyboardButton(text=f"✅ Correct ({l_spam})", callback_data="spam_check_t"),
                InlineKeyboardButton(text=f"❌ Incorrect ({l_ham})", callback_data="spam_check_f"),
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

        while True:
            try:
                msg = await self.bot.client.send_message(
                    chat_id=-1001314588569,
                    text=notice,
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup(keyb),
                )
            except FloodWait as flood:
                await asyncio.sleep(flood.x)  # type: ignore
                continue

            await asyncio.sleep(0.1)
            break

        try:
            async with asyncio.Lock():
                await self.db.insert_one(
                    {
                        "_id": content_hash,
                        "text": text,
                        "spam": [],
                        "ham": [],
                        "proba": probability,
                        "msg_id": [msg.message_id],
                        "date": util.time.sec(),
                    }
                )
        except DuplicateKeyError:
            await self.db.update_one({"_id": content_hash}, {"$push": {"msg_id": msg.message_id}})

        target = await message.chat.get_member(user)
        if util.tg.is_staff_or_admin(target):
            return

        if probability >= 0.9:
            await self.bot.log_stat("spam_detected")
            alert = (
                f"❗️**SPAM ALERT**❗️\n\n"
                f"**User:** `{identifier}`\n"
                f"**Message Hash:** `{content_hash}`\n"
                f"**Spam Probability:** `{proba_str}%`"
            )
            try:
                await message.delete()
            except (MessageDeleteForbidden, ChatAdminRequired, UserAdminInvalid):
                alert += "\n\nNot enough permission to delete message."
                reply_id = message.message_id
            else:
                await self.bot.log_stat("spam_deleted")
                alert += "\n\nThe message has been deleted."
                reply_id = None

            await self.bot.client.send_message(
                message.chat.id,
                alert,
                reply_to_message_id=reply_id,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("View Message", url=msg.link)]]
                ),
            )

    @command.filters(filters.staff_only)
    async def cmd_update_model(self, _: command.Context) -> str:
        token = self.bot.config.get("sp_token")
        url = self.bot.config.get("sp_url")
        if not (token and url):
            return "No token provided!"

        await self.__load_model(token, url)
        return "Done"

    @command.filters(filters.staff_only)
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
        pred = await self._predict(content.strip())
        if pred.size == 0:
            return "Prediction failed"

        proba = pred[0][1]
        text = f"#SPAM\n\n**CPU Prediction:** `{self.prob_to_string(proba)}`\n"
        if identifier:
            text += f"**Identifier:** `{identifier}`\n"

        text += f"**Message Hash:** `{content_hash}`\n\n**======= CONTENT =======**\n\n{content}"
        _, msg, __, ___ = await asyncio.gather(
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
            self.bot.log_stat("spam_detected"),
            self.bot.log_stat("predicted"),
        )
        await ctx.respond(
            "Message logged as spam!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("View Message", url=msg.link)]]
            ),
        )
        return None

    @command.filters(aliases=["prediction"])
    async def cmd_predict(self, ctx: command.Context) -> Optional[str]:
        """Look a prediction for a replied message"""
        user = await self.user_db.find_one({"_id": ctx.author.id})
        if not user or user["reputation"] < 100:
            if not user:
                return None

            return await self.text(ctx.chat.id, "spampredict-unauthorized", user["reputation"])

        replied = ctx.msg.reply_to_message
        if not replied:
            await ctx.respond("Reply to a message!", delete_after=5)
            return None

        content = replied.text or replied.caption
        pred = await self._predict(content)
        if pred.size == 0:
            return "Prediction failed"

        await self.bot.log_stat("predicted")
        return (
            "**Result**\n\n"
            f"**Is Spam:** {await self._is_spam(content)}\n"
            f"**Spam Prediction:** `{self.prob_to_string(pred[0][1])}`\n"
            f"**Ham Prediction:** `{self.prob_to_string(pred[0][0])}`"
        )

    async def setting(self, chat_id: int, setting: bool) -> None:
        """Turn on/off spam prediction in chats"""
        await self.setting_db.update_one(
            {"chat_id": chat_id}, {"$set": {"setting": setting}}, upsert=True
        )

    async def is_active(self, chat_id: int) -> bool:
        """Return SpamShield setting"""
        data = await self.setting_db.find_one({"chat_id": chat_id})
        return data["setting"] if data else True

    @command.filters(filters.admin_only, aliases=["spampredict", "spam_predict"])
    async def cmd_spam_prediction(self, ctx: command.Context, enable: Optional[bool] = None) -> str:
        """Set spam prediction setting"""
        chat = ctx.chat
        if not ctx.input:
            return await self.text(chat.id, "spampredict-view", await self.is_active(chat.id))

        if enable is None:
            return await self.text(chat.id, "err-invalid-option")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "spampredict-set", "on" if enable else "off"),
            self.setting(chat.id, enable),
        )
        return ret
