"""Chat SpamShield"""
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
import hashlib
import pickle
import re
from datetime import datetime
from typing import Any, ClassVar, List, MutableMapping, Optional, TypeVar

from aiohttp import ClientResponseError
from pyrogram import filters
from pyrogram.errors import ChannelPrivate, UserNotParticipant
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)

try:
    from sklearn.pipeline import Pipeline

    _run_predict = True
except ImportError:
    Pipeline = TypeVar("Pipeline")
    _run_predict = False

from anjani import command, listener, plugin, util
from anjani.filters import admin_only, staff_only
from anjani.util import run_sync


class SpamShield(plugin.Plugin):
    name: ClassVar[str] = "SpamShield"

    db: util.db.AsyncCollection
    db_dump: util.db.AsyncCollection
    federation_db: util.db.AsyncCollection
    model: Optional[Pipeline] = None
    token: Optional[str] = None
    sp_token: Optional[str] = None
    sp_url: Optional[str] = None

    async def on_load(self) -> None:
        self.token = self.bot.config.get("sw_api")
        if not self.token:
            self.bot.log.warning("SpamWatch API token not exist")

        self.db = self.bot.db.get_collection("GBAN_SETTINGS")
        self.federation_db = self.bot.db.get_collection("FEDERATIONS")
        if _run_predict:
            self.sp_token = self.bot.config.get("sp_token")
            self.sp_url = self.bot.config.get("sp_url")
            self.db_dump = self.bot.db.get_collection("SPAM_DUMP")
            if self.sp_url and self.sp_token:
                await self._load_model()

    async def _load_model(self) -> None:
        self.log.info("Downloading spam prediction model!")
        async with self.bot.http.get(
            self.sp_url,  # type: ignore
            headers={
                "Authorization": f"token {self.sp_token}",
                "Accept": "application/vnd.github.v3.raw",
            },
        ) as res:
            if res.status == 200:
                self.model = await run_sync(pickle.loads, await res.read())
            else:
                self.model = None
                self.log.warning("Failed to download model")

    def _build_hash(self, content: str) -> str:
        return hashlib.sha256(content.strip().encode()).hexdigest()

    def _build_hex(self, user_id: int, chat_id: int) -> str:
        if user_id == chat_id:
            return hex(user_id)
        return f"{hex(user_id)}{chat_id: x}"

    def _predict(self, text: str) -> List[List[float]]:
        return self.model.predict_proba([text])  # type: ignore

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        setting = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        if not setting:
            return {}

        return {self.name: setting}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True)

    @listener.filters(filters.regex(r"spam_check_(t|f)\[(.*)\]"))
    async def on_callback_query(self, query: CallbackQuery) -> None:
        method = query.matches[0].group(1)
        message = query.message
        content_hash = re.compile(r"([A-Fa-f0-9]{64})").search(message.text)
        author = str(query.from_user.id)
        users_on_correct = users_on_incorrect = []
        total_correct = total_incorrect = 0

        if not content_hash:
            self.log.warning("Can't get hash from 'MessageID: %d'", message.message_id)
            return

        # Correct button data
        if message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup):
            data = message.reply_markup.inline_keyboard[0][0].callback_data
            if isinstance(data, bytes):
                data = data.decode()

            users_on_correct = re.findall("[0-9]+", data)

        # Incorrect button data
        if message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup):
            data = message.reply_markup.inline_keyboard[0][1].callback_data
            if isinstance(data, bytes):
                data = data.decode()

            users_on_incorrect = re.findall("[0-9]+", data)

        if method == "t":
            # Check user in incorrect data
            if author in users_on_incorrect:
                users_on_incorrect.remove(author)
            if author in users_on_correct:
                users_on_correct.remove(author)
            else:
                users_on_correct.append(author)
        elif method == "f":
            # Check user in correct data
            if author in users_on_correct:
                users_on_correct.remove(author)
            if author in users_on_incorrect:
                users_on_incorrect.remove(author)
            else:
                users_on_incorrect.append(author)
        else:
            raise ValueError("Unknown method")

        total_correct, total_incorrect = len(users_on_correct), len(users_on_incorrect)
        users_on_correct = f"[{', '.join(users_on_correct)}]"
        users_on_incorrect = f"[{', '.join(users_on_incorrect)}]"
        button = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=f"✅ Correct ({total_correct})",
                        callback_data=f"spam_check_t{users_on_correct}",
                    ),
                    InlineKeyboardButton(
                        text=f"❌ Incorrect ({total_incorrect})",
                        callback_data=f"spam_check_f{users_on_incorrect}",
                    ),
                ]
            ]
        )

        await asyncio.gather(
            self.db_dump.update_one(
                {"_id": content_hash[0]}, {"$set": {"spam": total_correct, "ham": total_incorrect}}
            ),
            query.edit_message_reply_markup(reply_markup=button),
        )

    async def on_chat_action(self, message: Message) -> None:
        """Checker service for new member"""
        chat = message.chat
        if message.left_chat_member or not await self.is_active(chat.id):
            return

        try:
            me = await chat.get_member("me")
            if not me.can_restrict_members:
                return

            for member in message.new_chat_members:
                await self.check(member, chat.id)
        except ChannelPrivate:
            return

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
        self.bot.loop.create_task(self.check_probability(chat.id, message.from_user.id, text))

        if not await self.is_active(chat.id):
            return

        try:
            me, target = await util.tg.fetch_permissions(self.bot.client, chat.id, user.id)
            if not me.can_restrict_members or util.tg.is_staff_or_admin(target, self.bot.staff):
                return

            await self.check(target.user, chat.id)
        except (ChannelPrivate, UserNotParticipant):
            return

    async def check_probability(self, chat: int, user: int, text: str) -> None:
        if not self.model:
            return

        response = await run_sync(self._predict, repr(text.strip()))
        probability = response[0][1]
        if probability <= 0.6:
            return

        content_hash = self._build_hash(text)

        data = await self.db_dump.find_one({"_id": content_hash})
        if data:
            return

        msg = (
            "#SPAM_PREDICTION\n\n"
            f"**Prediction Result**: {str(probability * 10 ** 2)[0:7]}\n"
            f"**Message Hash:** `{content_hash}`\n"
            f"**Identifier:** `{self._build_hex(user, chat)}`"
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
                                callback_data=f"spam_check_t[]",
                            ),
                            InlineKeyboardButton(
                                text="❌ Incorrect (0)",
                                callback_data=f"spam_check_f[]",
                            ),
                        ]
                    ]
                ),
            ),
            self.db_dump.update_one(
                {"_id": content_hash},
                {"$set": {"text": text, "spam": 0, "ham": 0, "chat": chat, "id": user}},
                upsert=True,
            ),
        )

    async def get_ban(self, user_id: int) -> MutableMapping[str, Any]:
        if not self.token:
            return {}

        path = f"https://api.spamwat.ch/banlist/{user_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        async with self.bot.http.get(path, headers=headers) as resp:
            if resp.status == 200 or resp.status == 201:
                return await resp.json()
            if resp.status == 204:
                return {}
            if resp.status == 401:
                raise ClientResponseError(
                    resp.request_info,
                    resp.history,
                    message="Make sure your Spamwatch API token is corret",
                )
            elif resp.status == 403:
                raise ClientResponseError(
                    resp.request_info,
                    resp.history,
                    message="Forbidden, your token permissions is not valid",
                )
            elif resp.status == 404:
                return {}
            elif resp.status == 429:
                until = (await resp.json()).get("until", 0)
                raise ClientResponseError(
                    resp.request_info,
                    resp.history,
                    message=f"Too many requests. Try again in {until - datetime.now()}",
                )
            else:
                raise ClientResponseError(resp.request_info, resp.history)

    async def cas_check(self, user: User) -> Optional[str]:
        """Check on CAS"""
        async with self.bot.http.get(f"https://api.cas.chat/check?user_id={user.id}") as res:
            data = await res.json()
            if data["ok"]:
                fullname = user.first_name + user.last_name if user.last_name else user.first_name
                reason = f"Automated fban https://cas.chat/query?u={user.id}"
                await self.federation_db.update_one(
                    {"_id": "AnjaniSpamShield"},
                    {
                        "$set": {
                            f"banned.{user.id}": {
                                "name": fullname,
                                "reason": reason,
                                "time": datetime.now(),
                            }
                        }
                    },
                )
                return reason

            return None

    async def is_active(self, chat_id: int) -> bool:
        """Return SpamShield setting"""
        data = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        return data["setting"] if data else False

    async def setting(self, chat_id: int, setting: bool) -> None:
        """Turn on/off SpamShield in chats"""
        await self.db.update_one({"chat_id": chat_id}, {"$set": {"setting": setting}}, upsert=True)

    async def check(self, user: User, chat_id: int) -> None:
        """Shield checker action."""
        cas, sw = await asyncio.gather(self.cas_check(user), self.get_ban(user.id))
        if not cas or not sw:
            return

        userlink = f"[{user.first_name}](tg://user?id={user.id})"
        reason = ""
        banner = ""
        if cas:
            banner = "[Combot Anti Spam](t.me/combot)"
            reason = f"[link]({cas})"
        if sw:
            if not banner:
                banner = "[Spam Watch](t.me/SpamWatch)"
                reason = sw["reason"]
            else:
                banner += " & [Spam Watch](t.me/SpamWatch)"
                reason += " & " + sw["reason"]

        await asyncio.gather(
            self.bot.client.kick_chat_member(chat_id, user.id),
            self.bot.client.send_message(
                chat_id,
                text=await self.text(chat_id, "banned-text", userlink, user.id, reason, banner),
                parse_mode="markdown",
                disable_web_page_preview=True,
            ),
        )

    @command.filters(admin_only)
    async def cmd_spamshield(self, ctx: command.Context, enable: Optional[bool] = None) -> str:
        """Set SpamShield setting"""
        chat = ctx.chat
        if not ctx.input:
            return await self.text(chat.id, "spamshield-view", await self.is_active(chat.id))

        if enable is None:
            return await self.text(chat.id, "err-invalid-option")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "spamshield-set", "on" if enable else "off"),
            self.setting(chat.id, enable),
        )
        return ret

    @command.filters(staff_only)
    async def cmd_spam(self, ctx: command.Context, *, content: str = ""):
        """Manual spam detection by bot staff"""
        if ctx.chat.type != "private":
            return "This command only avaliable on PM's!"
        if not self.model:
            return "Prediction model isn't available"

        user_id = None
        if ctx.msg.reply_to_message:
            content = ctx.msg.reply_to_message.text or ctx.msg.reply_to_message.caption
            if ctx.msg.reply_to_message.forward_from:
                user_id = ctx.msg.reply_to_message.forward_from.id
        else:
            if not content:
                return "Give me a text or reply to a message / forwarded message"

        content_hash = self._build_hash(content)
        pred = await run_sync(self._predict, repr(content.strip()))
        proba = pred[0][1]
        text = (
            "#SPAM\n\n"
            f"**CPU Prediction:** `{str(proba * 10 ** 2)[0:7]}`\n"
            f"**Message Hash:** `{content_hash}`\n"
            f"\n**====== CONTENT =======**\n\n{content}"
        )
        await asyncio.gather(
            self.db_dump.update_one(
                {"_id": content_hash},
                {
                    "$set": {
                        "text": content.strip(),
                        "spam": 1,
                        "ham": 0,
                        "chat": None,
                        "id": user_id,
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

    @command.filters(staff_only, aliases=["prediction"])
    async def cmd_predict(self, ctx: command.Context) -> Optional[str]:
        """Look a prediction for a replied message"""
        if not self.model:
            await ctx.respond("Prediction model isn't available", delete_after=5)
            return
        replied = ctx.msg.reply_to_message
        if not replied:
            await ctx.respond("Reply to a message!", delete_after=5)
            return
        content = replied.text or replied.caption
        pred = self._predict(repr(content))[0]
        return (
            f"**Spam Prediction:** `{str(pred[1] * 10 ** 2)[0:7]}`\n"
            f"**Ham Prediction:** `{str(pred[0] * 10 ** 2)[0:7]}`"
        )

    @command.filters(staff_only, aliases=["spaminfo"])
    async def cmd_sinfo(self, ctx: command.Context, *, arg: str = ""):
        """Get information fro spam identifier"""
        res = re.search(r"(0x[\da-f]+)(-[\da-f]+)?", arg, re.IGNORECASE)
        if not res:
            return
        user = await self.bot.client.get_users(int(res.group(1), 0))
        text = (
            "**User Info**\n\n"
            f"**Private ID: **`{res.group(1)}`\n"
            f"**User ID: **`{user.id}`\n"
            f"**First Name: **{user.first_name}\n"
        )
        if user.last_name:
            text += f"**Last Name: **{user.last_name}\n"
        text += f"**Username: **@{user.username}\n"
        text += f"**User Link: **{user.mention}\n"

        if res.group(2):
            chat = await self.bot.client.get_chat(int(res.group(2), 16))
            text += "\n**Chat Info**\n\n"
            text += f"**Private ID:** `{res.group(2)}`\n"
            text += f"**Chat ID:** `{chat.id}`\n"
            text += f"**Chat Type :** {chat.type}\n"
            text += f"**Chat Title :** {chat.title}\n"
            if chat.username:
                text += f"**Chat Username :** @{chat.username}\n"

        await ctx.respond(text)
