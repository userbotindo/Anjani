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
import re
from datetime import datetime
from typing import Any, ClassVar, MutableMapping, Optional

from aiohttp import ClientResponseError
from pyrogram import filters
from pyrogram.errors import ChannelPrivate
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User
)

from anjani import command, listener, plugin, util
from anjani.filters import admin_only


class SpamShield(plugin.Plugin):
    name: ClassVar[str] = "SpamShield"

    db: util.db.AsyncCollection
    db_dump: util.db.AsyncCollection
    federation_db: util.db.AsyncCollection
    token: str
    sp_token: Optional[str]
    sp_url: Optional[str]

    async def on_load(self) -> None:
        try:
            self.token = self.bot.config["sw_token"]
        except KeyError:
            self.bot.log.warning("SpamWatch API token not exist")
            return self.bot.unload_plugin(self)

        self.db = self.bot.db.get_collection("GBAN_SETTINGS")
        self.federation_db = self.bot.db.get_collection("FEDERATIONS")

        try:
            self.sp_token = self.bot.config["sp_token"]
            self.sp_url = self.bot.config["sp_url"]
        except KeyError:
            self.sp_token = None
            self.sp_url = None
        else:
            self.db_dump = self.bot.db.get_collection("SPAM_DUMP")

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
        await self.db.update_one({"chat_id": chat_id},
                                 {"$set": data[self.name]},
                                 upsert=True)

    @listener.filters(filters.regex(r"spam_check_(t|f)\[(.*?)\]"))
    async def on_callback_query(self, query: CallbackQuery) -> None:
        if isinstance(query.data, bytes):
            query.data = query.data.decode()

        message = query.message
        content_hash = re.compile(r"([A-Fa-f0-9]{64})").search(message.text)
        author = str(query.from_user.id)
        users_on_correct = users_on_incorrect = []
        total_correct = total_incorrect = 0

        if not content_hash:
            self.log.warning("Can't get hash from 'MessageID: %d'", message.message_id)
            return

        # Correct button data
        correct = re.compile(r"spam_check_t(.*?)").match(query.data)
        if message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup):
            data = message.reply_markup.inline_keyboard[0][0].callback_data
            if isinstance(data, bytes):
                data = data.decode()

            users_on_correct = re.findall("[0-9]+", data)

        # Incorrect button data
        incorrect = re.compile(r"spam_check_f(.*?)").match(query.data)
        if message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup):
            data = message.reply_markup.inline_keyboard[0][1].callback_data
            if isinstance(data, bytes):
                data = data.decode()

            users_on_incorrect = re.findall("[0-9]+", data)

        if correct:
            # Check user in incorrect data
            if author in users_on_incorrect:
                users_on_incorrect.remove(author)
            if author in users_on_correct:
                users_on_correct.remove(author)
            else:
                users_on_correct.append(author)
        elif incorrect:
            # Check user in correct data
            if author in users_on_correct:
                users_on_correct.remove(author)
            if author in users_on_incorrect:
                users_on_incorrect.remove(author)
            else:
                users_on_incorrect.append(author)

        total_correct, total_incorrect = len(users_on_correct), len(users_on_incorrect)
        users_on_correct = f"[{', '.join(users_on_correct)}]"
        users_on_incorrect = f"[{', '.join(users_on_incorrect)}]"
        button = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=f"✅ Correct ({total_correct})",
                        callback_data=f"spam_check_t{users_on_correct}"
                    ),
                    InlineKeyboardButton(
                        text=f"❌ Incorrect ({total_incorrect})",
                        callback_data=f"spam_check_f{users_on_incorrect}"
                    )
                ]
            ]
        )

        await asyncio.gather(
            self.db_dump.update_one(
                {"_id": content_hash[0]},
                {
                    "$set": {
                        "spam": total_correct,
                        "ham": total_incorrect
                    }
                }
            ),
            query.edit_message_reply_markup(reply_markup=button)
        )

    async def on_chat_action(self, message: Message) -> None:
        """Checker service for new member"""
        if message.left_chat_member:
            return
        chat = message.chat

        if not await self.is_active(chat.id):
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
        if not chat or message.left_chat_member or not message.from_user:
            return

        text = (
            message.text.strip()
            if message.text else
            (
                message.caption.strip()
                if message.media and message.caption else None
            )
        )
        if not text:
            return

        # Always check the spam probability but run it in the background
        self.bot.loop.create_task(self.check_probability(
            chat.id,
            message.from_user.id,
            text
            )
        )

        if not await self.is_active(chat.id):
            return

        try:
            user = message.from_user
            if not user:
                return

            me, target = await util.tg.fetch_permissions(
                self.bot.client,
                chat.id,
                user.id
            )
            if util.tg.is_staff_or_admin(target, self.bot.staff):
                return

            if not me.can_restrict_members:
                return

            await self.check(target.user, chat.id)
        except ChannelPrivate:
            return

    async def check_probability(self, chat: int, user: int, text: str) -> None:
        if not self.sp_token or not self.sp_url:
            return

        async with self.bot.http.post(
            self.sp_url,
            headers={"Authorization": f"Bearer {self.sp_token}"},
            json={"msg": text}
        ) as res:
            if res.status != 200:
                return

            response = await res.json()
            probability = response["spam_probability"]
            if probability <= 0.6:
                return

        content_hash = response["text_hash"]
        data = await self.db_dump.find_one({"_id": content_hash})
        if data:
            return

        msg = (
            "#SPAM_PREDICTION\n\n"
            f"**Prediction Result**: {str(probability * 10 ** 2)[0:7]}\n"
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
                                callback_data=f"spam_check_t[]",
                            ),
                            InlineKeyboardButton(
                                text="❌ Incorrect (0)",
                                callback_data=f"spam_check_f[]",
                            )
                        ]
                    ]
                )
            ),
            self.db_dump.update_one(
                {"_id": content_hash},
                {
                    "$set": {
                        "text": text,
                        "spam": 0,
                        "ham": 0,
                        "chat": chat,
                        "id": user
                    }
                },
                upsert=True
            )
        )

    async def get_ban(self, user_id: int) -> MutableMapping[str, Any]:
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
                    message="Make sure your Spamwatch API token is corret"
                )
            elif resp.status == 403:
                raise ClientResponseError(
                    resp.request_info,
                    resp.history,
                    message="Forbidden, your token permissions is not valid"
                )
            elif resp.status == 404:
                return {}
            elif resp.status == 429:
                until = (await resp.json()).get("until", 0)
                raise ClientResponseError(
                    resp.request_info,
                    resp.history,
                    message=f"Too many requests. Try again in {until - datetime.now()}"
                )
            else:
                raise ClientResponseError(resp.request_info, resp.history)

    async def cas_check(self, user: User) -> Optional[str]:
        """Check on CAS"""
        async with self.bot.http.get(f"https://api.cas.chat/check?user_id={user.id}") as res:
            data = await res.json()
            if data["ok"]:
                fullname = (
                    user.first_name + user.last_name
                    if user.last_name else user.first_name
                )
                reason = f"https://cas.chat/query?u={user.id}"
                await self.federation_db.update_one(
                    {"_id": "AnjaniSpamShield"},
                    {
                        "$set": {
                            f"banned.{user.id}": {
                                "name": fullname,
                                "reason": reason,
                                "time": datetime.now()
                            }
                        }
                    }
                )
                return reason

            return None

    async def is_active(self, chat_id: int) -> bool:
        """Return SpamShield setting"""
        data = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        return data["setting"] if data else False

    async def setting(self, chat_id: int, setting: bool) -> None:
        """Turn on/off SpamShield in chats"""
        await self.db.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "setting": setting
                }
            },
            upsert=True
        )

    async def check(self, user: User, chat_id: int) -> None:
        """Shield checker action."""
        cas, sw = await asyncio.gather(self.cas_check(user),
                                       self.get_ban(user.id))
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
                text=await self.text(
                    chat_id,
                    "banned-text",
                    userlink,
                    user.id,
                    reason,
                    banner
                ),
                parse_mode="markdown",
                disable_web_page_preview=True,
            )
        )

    @command.filters(admin_only)
    async def cmd_spamshield(self, ctx: command.Context, enable: Optional[bool] = None) -> str:
        """Set SpamShield setting"""
        chat = ctx.chat
        if not ctx.input:
            return await self.text(chat.id, "spamshield-view", await self.is_active(chat.id))

        if enable is None:
            return await self.text(chat.id, "err-invalid-option")

        ret, _ = await asyncio.gather(self.text(chat.id,
                                                "spamshield-set",
                                                "on" if enable else "off"),
                                      self.setting(chat.id, enable))
        return ret
