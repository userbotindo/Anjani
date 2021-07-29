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
from datetime import datetime
from typing import Any, ClassVar, MutableMapping, Optional

from aiohttp import ClientResponseError
from motor.motor_asyncio import AsyncIOMotorCollection
from pyrogram import filters
from pyrogram.errors import ChannelPrivate
from pyrogram.types import Message, User

from anjani import command, listener, plugin
from anjani.custom_filter import admin_only


class SpamShield(plugin.Plugin):
    name: ClassVar[str] = "SpamShield"

    db: AsyncIOMotorCollection
    token: str

    async def on_load(self) -> None:
        try:
            self.token = self.bot.config["sw_api"]
        except AttributeError:
            self.bot.log.warning("SpamWatch API token not exist")
            return self.bot.unload_plugin(self)

        self.db = self.bot.db.get_collection("GBAN_SETTINGS")

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        return {self.name: await self.db.find_one({"chat_id": chat_id},
                                                  {"_id": False})}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id},
                                 {"$set": data[self.name]},
                                 upsert=True)

    async def on_chat_action(self, message: Message) -> None:
        """Checker service for new member"""
        if message.left_chat_member:
            return
        chat = message.chat

        if not await self.is_active(chat.id):
            return

        try:
            me = await message.chat.get_member("me")
            if me.can_restrict_members:
                for member in message.new_chat_members:
                    await self.check(member, chat.id)
            else:
                return
        except ChannelPrivate:
            return

    @listener.filters(filters.group)
    async def on_message(self, message: Message) -> None:
        """Checker service for message"""
        chat = message.chat
        if not chat or message.left_chat_member:
            return

        if not await self.is_active(chat.id):
            return

        try:
            me = await message.chat.get_member("me")
            if me.can_restrict_members:
                user = message.from_user
                if not user:
                    return

                target = await chat.get_member(user.id)
                if (target.status in {"creator", "administrator"} or
                        target.user.id in self.bot.staff):
                    return

                return await self.check(target.user, chat.id)
            else:
                return
        except ChannelPrivate:
            return

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

    async def cas_check(self, user_id: int) -> Optional[str]:
        """Check on CAS"""
        async with self.bot.http.get(f"https://api.cas.chat/check?user_id={user_id}") as res:
            data = await res.json()
            return "https://cas.chat/query?u={}".format(user_id) if data["ok"] else None

    async def is_active(self, chat_id: int) -> bool:
        """Return SpamShield setting"""
        data: Optional[
            MutableMapping[
                str,
                bool
            ]
        ] = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
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
        cas, sw = await asyncio.gather(self.cas_check(user.id),
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

        text = await self.text(chat_id, "banned-text", userlink, user.id, reason, banner)
        await asyncio.gather(
            self.bot.client.kick_chat_member(chat_id, user.id),
            self.bot.client.send_message(
                chat_id,
                text=text,
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
