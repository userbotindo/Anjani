"""Spam Prediction plugin"""
# Copyright (C) 2020 - 2022  UserbotIndo Team, <https://github.com/userbotindo.git>
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
import unicodedata
from datetime import datetime, time, timedelta
from functools import partial
from hashlib import md5, sha256
from pathlib import Path
from random import randint
from typing import Any, Callable, ClassVar, List, MutableMapping, Optional

from aiopath import AsyncPath
from pymongo.errors import DuplicateKeyError
from pyrogram.errors import (
    ChatAdminRequired,
    FloodWait,
    MessageDeleteForbidden,
    MessageIdInvalid,
    MessageNotModified,
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
    from scipy.stats import ttest_1samp
    from sklearn.pipeline import Pipeline

    _run_predict = True
except ImportError:
    from anjani.util.types import Pipeline

    _run_predict = False

from anjani import command, filters, listener, plugin, util
from anjani.util.misc import StopPropagation

env = Path("config.env")
try:
    token = re.search(r'^(?!#)\s+?SP_TOKEN="(\w+)"', env.read_text().strip(), re.MULTILINE).group(  # type: ignore
        1
    )
except (AttributeError, FileNotFoundError):
    token = ""

del env


def get_trust(sample: List[float]) -> Optional[float]:
    """Compute the trust score of a user
    Args:
        sample (List[float]): A list of scores
    Returns:
        Optional[float]: The trust score of the user
    """
    if not _run_predict:
        return None
    if len(sample) < 3:
        return None  # Not enough data
    _, pred = ttest_1samp(sample, 0.5, alternative="greater")
    return pred * 100


class SpamPrediction(plugin.Plugin):
    name: ClassVar[str] = "SpamPredict"
    helpable: ClassVar[bool] = True
    disabled: ClassVar[bool] = not _run_predict or not token

    db: util.db.AsyncCollection
    user_db: util.db.AsyncCollection
    setting_db: util.db.AsyncCollection
    model: Pipeline

    async def on_load(self) -> None:
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
        async with self.bot.http.post(
            "https://spamdetect.userbotindo.com",
            headers={"Authorization": f"Bearer {token}"},
        ) as res:
            if res.status == 200:
                self.model = await util.run_sync(pickle.loads, await res.read())
            else:
                self.log.warning("Failed to download prediction model!")
                self.bot.unload_plugin(self)

    def _check_spam_results_ocr(
        self, message: Message, future: asyncio.Future[Optional[str]]
    ) -> None:
        def done(fut: asyncio.Future[None]) -> None:
            try:
                fut.result()
            except Exception as e:  # skipcq: PYL-W0703
                if isinstance(e, StopPropagation):
                    raise e

                self.log.error("Unexpected error occured when checking OCR results", exc_info=e)

        text = future.result()
        if not text:
            return

        self.bot.loop.create_task(self.spam_check(message, text, from_ocr=True)).add_done_callback(
            partial(self.bot.loop.call_soon_threadsafe, done)
        )

    @staticmethod
    def _build_hash(content: str) -> str:
        return sha256(content.strip().encode()).hexdigest()

    def _build_hex(self, id: Optional[int]) -> str:
        if not id:
            id = self.bot.uid
        # skipcq: PTC-W1003
        return md5((str(id) + self.bot.user.username).encode()).hexdigest()  # skipcq: BAN-B324

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text to remove accents and other non-ASCII characters."""
        return (
            unicodedata.normalize("NFKD", text).encode("utf-8", "ignore").decode("utf-8", "ignore")
        ).lower()

    @staticmethod
    def prob_to_string(value: float) -> str:
        return str(value * 10**2)[0:7]

    async def _predict(self, text: str) -> util.types.NDArray[float]:
        return await util.run_sync(self.model.predict_proba, [text])

    async def _is_spam(self, text: str) -> bool:
        return (await util.run_sync(self.model.predict, [text]))[0] == "spam"

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

    async def run_ocr(self, message: Message) -> Optional[str]:
        """Run tesseract"""
        try:
            image = AsyncPath(await message.download())
        except Exception:  # skipcq: PYL-W0703
            return self.log.warning(
                "Failed to download image from MessageID %s in Chat %s",
                message.id,
                message.chat.id,
            )

        try:
            stdout, _, exitCode = await util.system.run_command(
                "tesseract", str(image), "stdout", "-l", "eng+ind", "--psm", "6"
            )
        except FileNotFoundError:
            return
        except Exception as e:  # skipcq: PYL-W0703
            return self.log.error("Unexpected error occured when running OCR", exc_info=e)
        finally:
            await image.unlink()

        if exitCode != 0:
            return self.log.warning("tesseract returned code '%s', %s", exitCode, stdout)

        return stdout

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
            await handler[handle](query, data[handle])

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
            return await query.answer("The voting poll for this message has ended!")

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
                            "Please wait i'm updating the content for you.",
                            show_alert=True,
                        )
                        await asyncio.sleep(flood.value)  # type: ignore
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

    @listener.filters(filters.group & ~filters.outgoing)
    @listener.priority(70)
    async def on_message(self, message: Message) -> None:
        """Checker service for message"""
        setting = await self.setting_db.find_one({"chat_id": message.chat.id})
        if setting and not setting.get("setting"):
            return

        chat = message.chat
        text = (
            message.text
            if message.text
            else (message.caption if message.media and message.caption else None)
        )
        if message.photo:
            self.bot.loop.create_task(self.run_ocr(message)).add_done_callback(
                partial(self.bot.loop.call_soon_threadsafe, self._check_spam_results_ocr, message)
            )

        if not chat or message.left_chat_member or not text:
            return

        # Always check the spam probability
        return await self.spam_check(message, text)

    async def spam_check(self, message: Message, text: str, *, from_ocr: bool = False) -> None:
        text = text.strip()
        try:
            user = message.from_user.id
        except AttributeError:
            user = None

        text_norm = self._normalize_text(text)
        if len(text_norm.split()) < 5:  # Skip short messages
            return

        response = await self._predict(text_norm)
        if response.size == 0:
            return

        probability = response[0][1]

        await self._collect_random_sample(probability, user)

        if probability <= 0.5:
            return

        content_hash = self._build_hash(text)
        identifier = self._build_hex(user)
        proba_str = self.prob_to_string(probability)
        msg = None

        if message.chat.username:

            notice = (
                "#SPAM_PREDICTION\n\n"
                f"**Prediction Result**: {proba_str}\n"
                f"**Identifier**: `{identifier}`\n"
            )
            if ch := message.forward_from_chat:
                notice += f"**Channel ID**: `{self._build_hex(ch.id)}`\n"

            if from_ocr:
                notice += (
                    f"**Photo Text Hash**: `{content_hash}`\n\n**====== CONTENT =======**\n\n{text}"
                )
            else:
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
                    InlineKeyboardButton(
                        text=f"✅ Correct ({l_spam})", callback_data="spam_check_t"
                    ),
                    InlineKeyboardButton(
                        text=f"❌ Incorrect ({l_ham})", callback_data="spam_check_f"
                    ),
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

            while True:
                try:
                    msg = await self.bot.client.send_message(
                        chat_id=-1001314588569,
                        text=notice,
                        disable_web_page_preview=True,
                        reply_markup=InlineKeyboardMarkup(keyb),
                    )
                except FloodWait as flood:
                    await asyncio.sleep(flood.value)  # type: ignore
                    continue

                await asyncio.sleep(0.1)
                break

            try:
                async with asyncio.Lock():
                    await self.db.insert_one(
                        {
                            "_id": content_hash,
                            "user": identifier,
                            "text": text_norm,
                            "spam": [],
                            "ham": [],
                            "proba": probability,
                            "msg_id": [msg.id],
                            "date": util.time.sec(),
                        }
                    )
            except DuplicateKeyError:
                await self.db.update_one({"_id": content_hash}, {"$push": {"msg_id": msg.id}})

        if probability >= 0.8:
            chat = message.chat
            if not user and message.sender_chat:
                if message.sender_chat.id == chat.id:  # anon admin
                    return

                current_chat: Any = await self.bot.client.get_chat(chat.id)
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

            if from_ocr:
                alert = (
                    f"❗️**PHOTO SPAM ALERT**❗️\n\n"
                    f"**User**: `{identifier}`\n"
                    f"**Photo Text Hash**: `{content_hash}`\n"
                    f"**Spam Probability**: `{proba_str}%`"
                )
            else:
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
            if message.chat.username and msg:
                button.append([InlineKeyboardButton("View Message", url=msg.link)])

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

    async def mark_spam_ocr(
        self, content: str, user_id: Optional[int], chat_id: int, message_id: int
    ) -> bool:
        identifier = self._build_hex(user_id)
        content_hash = self._build_hash(content)
        pred = await self._predict(content)
        if pred.size == 0:
            return False

        proba = pred[0][1]
        text = f"#SPAM\n\n**CPU Prediction**: `{self.prob_to_string(proba)}`\n"
        if identifier:
            text += f"**Identifier**: `{identifier}`\n"

        text += f"**Photo Text Hash**: `{content_hash}`\n\n**======= CONTENT =======**\n\n{content}"
        res = await asyncio.gather(
            self.bot.client.send_message(
                chat_id=-1001314588569,
                text=text,
                disable_web_page_preview=True,
            ),
            self.db.update_one(
                {"_id": content_hash},
                {
                    "$set": {
                        "text": content,
                        "spam": 1,
                        "ham": 0,
                    }
                },
                upsert=True,
            ),
            self.bot.log_stat("spam_detected"),
            self.bot.log_stat("predicted"),
        )
        await self.bot.client.send_message(
            chat_id,
            "Message photo logged as spam!",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("View Message", url=res[0].link)]]
            ),
            reply_to_message_id=message_id,
        )
        return True

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

        if reply_msg and reply_msg.photo:
            ocr_result = await self.run_ocr(reply_msg)
            if ocr_result:
                try:
                    await self.mark_spam_ocr(ocr_result, user_id, ctx.chat.id, reply_msg.id)
                except Exception as e:  # skipcq: PYL-W0703
                    self.log.error("Failed to marked OCR results as spam", exc_info=e)

                # Return early if content is empty, so error message not shown
                if not content:
                    return None

        if not content:
            return await ctx.get_text("spampredict-empty")

        identifier = self._build_hex(user_id)
        content_hash = self._build_hash(content)
        content_normalized = self._normalize_text(content.strip())
        pred = await self._predict(content_normalized)
        if pred.size == 0:
            return "Prediction failed"

        proba = pred[0][1]
        text = f"#SPAM\n\n**CPU Prediction**: `{self.prob_to_string(proba)}`\n"
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
        chat = ctx.chat
        user = await self.user_db.find_one({"_id": ctx.author.id})
        if not user:
            return None

        if user["reputation"] < 100:
            return await self.text(chat.id, "spampredict-unauthorized", user["reputation"])

        replied = ctx.msg.reply_to_message
        if not replied:
            await ctx.respond(await ctx.get_text("error-reply-to-message"), delete_after=5)
            return None

        content = replied.text or replied.caption

        photo_prediction = None
        if replied.photo:
            await ctx.respond(
                await ctx.get_text("spampredict-photo"),
                reply_to_message_id=replied.id,
            )

            ocr_result = await self.run_ocr(replied)
            if ocr_result:
                ocr_prediction = await self._predict(ocr_result)
                if ocr_prediction.size != 0:
                    photo_prediction = (
                        "**Result Photo Text**\n\n"
                        f"**Is Spam**: {await self._is_spam(ocr_result)}\n"
                        f"**Spam Prediction**: `{self.prob_to_string(ocr_prediction[0][1])}`\n"
                        f"**Ham Prediction**: `{self.prob_to_string(ocr_prediction[0][0])}`\n\n"
                    )
                    # Return early if content is empty, so error message not shown
                    if not content:
                        await asyncio.gather(
                            self.bot.log_stat("predicted"),
                            ctx.respond(photo_prediction),
                        )
                        return None
            else:
                photo_prediction = await ctx.get_text("spampredict-photo-failed")

        if not content:
            return await ctx.get_text("spampredict-empty")

        content = self._normalize_text(content.strip())
        pred = await self._predict(content)
        if pred.size == 0:
            return await ctx.get_text("spampredict-failed")

        textPrediction = (
            f"**Is Spam**: {await self._is_spam(content)}\n"
            f"**Spam Prediction**: `{self.prob_to_string(pred[0][1])}`\n"
            f"**Ham Prediction**: `{self.prob_to_string(pred[0][0])}`"
        )
        await asyncio.gather(
            self.bot.log_stat("predicted"),
            ctx.respond(
                photo_prediction + "**Result Caption Text**\n\n" + textPrediction
                if photo_prediction
                else "**Result**\n\n" + textPrediction,
                reply_to_message_id=None if replied.photo else replied.id,
            ),
        )
        return None

    async def setting(self, chat_id: int, setting: bool) -> None:
        """Turn on/off spam prediction in chats"""
        if setting:
            await self.setting_db.update_one(
                {"chat_id": chat_id}, {"$set": {"setting": True}}, upsert=True
            )
        else:
            await self.setting_db.delete_one({"chat_id": chat_id})

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
