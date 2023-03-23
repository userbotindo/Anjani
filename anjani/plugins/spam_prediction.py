"""Spam Prediction plugin"""
# Copyright (C) 2020 - 2023  UserbotIndo Team, <https://github.com/userbotindo.git>
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
import re
from datetime import datetime, time, timedelta
from hashlib import md5, sha256
from random import randint
from typing import Any, Callable, ClassVar, List, MutableMapping, Optional, Tuple

from pyrogram.errors import (
    ChatAdminRequired,
    FloodWait,
    MessageDeleteForbidden,
    PeerIdInvalid,
    QueryIdInvalid,
    UserAdminInvalid,
    UserNotParticipant,
)
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

try:
    from userbotindo import Classifier

    _run_predict = True
except ImportError:
    from anjani.util.types import Classifier

    _run_predict = False

from anjani import command, filters, listener, plugin, util
from anjani.util.misc import StopPropagation


class SpamPrediction(plugin.Plugin):
    name: ClassVar[str] = "SpamPredict"
    helpable: ClassVar[bool] = True
    disabled: ClassVar[bool] = not _run_predict

    db: util.db.AsyncCollection
    user_db: util.db.AsyncCollection
    setting_db: util.db.AsyncCollection
    model: Classifier

    __predict_cost: int = 10
    __log_channel: int = -1001314588569

    async def on_load(self) -> None:
        self.model = Classifier()
        self.db = self.bot.db.get_collection("SPAM_DUMP")
        self.user_db = self.bot.db.get_collection("USERS")
        self.setting_db = self.bot.db.get_collection("SPAM_PREDICT_SETTING")

        await self.__load_model()
        self.bot.loop.create_task(self.__refresh_model())

    async def on_chat_migrate(self, message: Message) -> None:
        await self.db.update_one(
            {"chat_id": message.migrate_from_chat_id},
            {"$set": {"chat_id": message.chat.id}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        setting = await self.setting_db.find_one({"chat_id": chat_id}, {"_id": False})
        return {self.name: setting} if setting else {}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.setting_db.update_one(
            {"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True
        )

    async def __refresh_model(self) -> None:
        scheduled_time = time(hour=17)  # Run at 00:00 WIB
        while True:
            now = datetime.utcnow()
            date = now.date()
            if now.time() > scheduled_time:
                date = now.date() + timedelta(days=1)
            then = datetime.combine(date, scheduled_time)
            self.log.debug("Next model refresh at %s UTC", then)
            await asyncio.sleep((then - now).total_seconds())
            await self.__load_model()

    async def __load_model(self) -> None:
        self.log.info("Downloading spam prediction model!")
        try:
            await self.model.load_model(self.bot.http)
        except RuntimeError:
            self.log.warning("Failed to download prediction model!")
            self.bot.unload_plugin(self)

    @staticmethod
    def _build_hash(content: str) -> str:
        return sha256(content.strip().encode()).hexdigest()

    def _build_hex(self, id: Optional[int]) -> str:
        if not id:
            id = self.bot.uid
        # skipcq: PTC-W1003
        return md5((str(id) + self.bot.user.username).encode()).hexdigest()  # skipcq: BAN-B324

    async def _collect_random_sample(self, proba: float, uid: Optional[int]) -> None:
        if not uid or uid == self.bot.uid:
            return
        if randint(1, 2) == 2:  # 50% chance to collect a sample
            await self.user_db.update_one(
                {"_id": uid},
                {
                    "$push": {
                        "pred_sample": {
                            "$each": [proba],
                            "$slice": -10,  # Only keep the last 10 samples
                        }
                    }
                },
            )  # Do not upsert

    @listener.filters(
        filters.regex(r"spam_check_(?P<value>t|f)") | filters.regex(r"spam_ban_(?P<user>.*)")
    )
    async def on_callback_query(self, query: CallbackQuery) -> None:
        data = query.matches[0].groupdict()
        handler: MutableMapping[str, Callable] = {
            "value": self._spam_vote_handler,
            "user": self._spam_ban_handler,
        }
        for handle in data.keys():
            try:
                await handler[handle](query, data[handle])
            except QueryIdInvalid:
                pass

    async def _spam_ban_handler(self, query: CallbackQuery, user: str) -> None:
        chat = query.message.chat
        try:
            invoker = await chat.get_member(query.from_user.id)
        except UserNotParticipant:
            return await query.answer(
                await self.get_text(chat.id, "error-no-rights"), show_alert=True
            )

        if not invoker.privileges or not invoker.privileges.can_restrict_members:
            return await query.answer(await self.get_text(chat.id, "spampredict-ban-no-perm"))

        keyboard = query.message.reply_markup
        if not isinstance(keyboard, InlineKeyboardMarkup):
            raise ValueError("Reply markup must be an InlineKeyboardMarkup")

        try:
            target = await self.bot.client.get_users(int(user))
        except PeerIdInvalid:
            await query.answer("Error while fetching user!")
            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(keyboard.inline_keyboard[:-1])
            )
            return
        if isinstance(target, list):
            target = target[0]

        await chat.ban_member(target.id)
        await query.answer(
            await self.get_text(
                chat.id, "spampredict-ban", user=target.username or target.first_name
            )
        )

        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(keyboard.inline_keyboard[:-1])
        )

    async def _spam_vote_handler(self, query: CallbackQuery, value: str) -> None:
        message = query.message
        content = re.compile(r"([A-Fa-f0-9]{64})").search(message.text)
        author = query.from_user.id

        if not content:
            return await query.answer(f"Can't get hash from MessageID: '{message.id}'")

        content_hash = content[0]

        data = await self.db.find_one({"_id": content_hash})
        if not data:
            return await query.answer(
                "The voting poll for this message has ended!", show_alert=True
            )

        users_on_correct = data["spam"]
        users_on_incorrect = data["ham"]
        if value == "t":
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
        elif value == "f":
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
            return await query.answer("Invalid keyboard method!", show_alert=True)

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

        await self.bot.client.edit_message_reply_markup(
            self.__log_channel, data["msg_id"], InlineKeyboardMarkup(button)
        )

        await query.answer()

    @listener.filters(filters.group & ~filters.outgoing)
    @listener.priority(70)
    async def on_message(self, message: Message) -> None:
        """Checker service for message"""
        if not await self.is_active(message.chat.id):
            return

        chat = message.chat
        text = (
            message.text
            if message.text
            else (message.caption if message.media and message.caption else None)
        )
        if not chat or message.left_chat_member:
            return

        if not text:
            return

        # Always check the spam probability
        await self.spam_check(message, text)

    async def _build_notice(
        self, message: Message, text: str, proba_str: str, identifier: str, content_hash: str
    ) -> Tuple[str, List[List[InlineKeyboardButton]]]:
        notice = (
            "#SPAM_PREDICTION\n\n"
            f"**Prediction Result**: {proba_str}\n"
            f"**Identifier**: `{identifier}`\n"
        )
        if ch := message.forward_from_chat:
            notice += f"**Channel ID**: `{self._build_hex(ch.id)}`\n"

        notice += f"**Message Text Hash**: `{content_hash}`\n\n**====== CONTENT =======**\n\n{text}"
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
            ],
            [InlineKeyboardButton(text="Chat", url=f"https://t.me/{message.chat.username}")],
        ]

        if message.forward_from_chat and message.forward_from_chat.username:
            raw_btn = InlineKeyboardButton(
                text="Channel", url=f"https://t.me/{message.forward_from_chat.username}"
            )
            if message.chat.username:
                keyb[1].append(raw_btn)
            else:
                keyb.append([raw_btn])

        return notice, keyb

    async def spam_check(self, message: Message, text: str) -> None:
        text = text.strip()
        try:
            user = message.from_user.id
        except AttributeError:
            user = None

        text_norm = self.model.normalize(text)
        if len(text_norm.split()) < 4:  # Skip short messages
            return

        response = await self.model.predict(text_norm)
        if response.size == 0:
            return

        probability = response[0][1]

        await self._collect_random_sample(probability, user)

        if probability <= 0.5:
            return

        content_hash = self._build_hash(text)
        identifier = self._build_hex(user)
        proba_str = self.model.prob_to_string(probability)
        msg_id = None

        # only log public chat
        if message.chat.username:
            notice, keyb = await self._build_notice(
                message, text, proba_str, identifier, content_hash
            )

            async with asyncio.Lock():
                data = await self.db.find_one({"_id": content_hash})
                if data:
                    msg_id = data["msg_id"]
                else:
                    while True:
                        try:
                            msg = await self.bot.client.send_message(
                                chat_id=self.__log_channel,
                                text=notice,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(keyb),
                            )
                            msg_id = msg.id
                        except FloodWait as flood:
                            await asyncio.sleep(flood.value)  # type: ignore
                            continue

                        await asyncio.sleep(0.1)
                        break

                    await self.db.insert_one(
                        {
                            "_id": content_hash,
                            "user": identifier,
                            "spam": [],
                            "ham": [],
                            "proba": probability,
                            "msg_id": msg.id,
                            "date": util.time.sec(),
                            "text": text_norm,
                        },
                    )

        if probability >= 0.8:
            chat = message.chat
            if not user and message.sender_chat:
                if message.sender_chat.id == chat.id:  # anon admin
                    return

                current_chat: Any = await self.bot.get_chat(chat.id)
                if (
                    current_chat.linked_chat
                    and message.sender_chat.id == current_chat.linked_chat.id
                ):
                    # Linked channel group
                    return

            target = None
            if user:
                try:
                    target = await message.chat.get_member(user)
                except UserNotParticipant:
                    pass
                else:
                    if util.tg.is_staff_or_admin(target):
                        return

            alert = (
                f"❗️**MESSAGE SPAM ALERT**❗️\n\n"
                f"**User**: `{identifier}`\n"
                f"**Message Text Hash**: `{content_hash}`\n"
                f"**Spam Probability**: `{proba_str}%`"
            )

            await self.bot.log_stat("spam_detected")
            try:
                await message.delete()
            except (MessageDeleteForbidden, ChatAdminRequired, UserAdminInvalid):
                alert += "\n\nNot enough permission to delete message."
                reply_id = message.id
            else:
                await self.bot.log_stat("spam_deleted")
                alert += "\n\nThe message has been deleted."
                reply_id = 0

            chat = message.chat
            button = []
            me = await chat.get_member(self.bot.uid)
            if message.chat.username and msg_id:
                button.append(
                    [
                        InlineKeyboardButton(
                            "View Message", url=f"https://t.me/SpamPredictionLog/{msg_id}"
                        )
                    ]
                )

            if me.privileges and me.privileges.can_restrict_members and target is not None:
                button.append(
                    [
                        InlineKeyboardButton(
                            "Ban User (*admin only)", callback_data=f"spam_ban_{user}"
                        )
                    ]
                )

            await self.bot.client.send_message(
                chat.id,
                alert,
                reply_to_message_id=reply_id,
                reply_markup=InlineKeyboardMarkup(button),
            )
            raise StopPropagation

    @command.filters(filters.staff_only)
    async def cmd_update_model(self, ctx: command.Context) -> Optional[str]:
        await self.__load_model()
        await ctx.respond("Done", delete_after=5)

    @command.filters(filters.staff_only)
    async def cmd_spam(self, ctx: command.Context) -> Optional[str]:
        """Manual spam detection by bot staff"""
        user_id = None
        reply_msg = ctx.msg.reply_to_message
        if reply_msg:
            content = reply_msg.text or reply_msg.caption
            if reply_msg.from_user and reply_msg.from_user.id != ctx.author.id:
                user_id = reply_msg.from_user.id
            elif reply_msg.forward_from:
                user_id = reply_msg.forward_from.id
        else:
            content = ctx.input

        if not content:
            return await ctx.get_text("spampredict-empty")

        identifier = self._build_hex(user_id)
        content_hash = self._build_hash(content)
        content_normalized = self.model.normalize(content.strip())
        pred = await self.model.predict(content_normalized)
        if pred.size == 0:
            return "Prediction failed"

        proba = pred[0][1]
        text = f"#SPAM\n\n**CPU Prediction**: `{self.model.prob_to_string(proba)}`\n"
        if identifier:
            text += f"**Identifier**: `{identifier}`\n"

        text += f"**Message Hash**: `{content_hash}`\n\n**======= CONTENT =======**\n\n{content}"
        _, msg, __, ___ = await asyncio.gather(
            self.db.update_one(
                {"_id": content_hash},
                {
                    "$set": {
                        "text": content_normalized,
                        "spam": 1,
                        "ham": 0,
                    }
                },
                upsert=True,
            ),
            self.bot.client.send_message(
                chat_id=self.__log_channel,
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
        chat = ctx.chat
        user = await self.user_db.find_one({"_id": ctx.author.id})
        if not user:
            return None

        if user.get("reputation", 0) < self.__predict_cost:
            return await self.text(
                chat.id,
                "spampredict-insuficent",
                self.__predict_cost,
                user.get("reputation", 0),
            )

        replied = ctx.msg.reply_to_message
        if not replied:
            await ctx.respond(await ctx.get_text("error-reply-to-message"), delete_after=5)
            return None

        content = replied.text or replied.caption
        if not content:
            return await ctx.get_text("spampredict-empty")
        content = self.model.normalize(content.strip())
        pred = await self.model.predict(content)
        if pred.size == 0:
            return await ctx.get_text("spampredict-failed")

        textPrediction = (
            f"**Is Spam**: {await self.model.is_spam(content)}\n"
            f"**Spam Prediction**: `{self.model.prob_to_string(pred[0][1])}`\n"
            f"**Ham Prediction**: `{self.model.prob_to_string(pred[0][0])}`"
        )
        await asyncio.gather(
            self.bot.log_stat("predicted"),
            ctx.respond(
                "**Result**\n\n" + textPrediction,
                reply_to_message_id=replied.id,
            ),
            self.user_db.update_one(
                {"_id": ctx.author.id}, {"$inc": {"reputation": -self.__predict_cost}}
            ),
        )
        return None

    async def setting(self, chat_id: int, setting: bool) -> None:
        """Turn on/off spam prediction in chats"""
        await self.setting_db.update_one(
            {"chat_id": chat_id}, {"$set": {"setting": setting}}, upsert=True
        )

    async def is_active(self, chat_id: int) -> bool:
        """Return SpamShield setting"""
        data = await self.setting_db.find_one({"chat_id": chat_id})
        return data.get("setting", True) if data else True

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
