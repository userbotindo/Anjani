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
from json import JSONDecodeError
from typing import Any, ClassVar, MutableMapping, Optional

from aiohttp import ClientOSError, ClientResponseError, ContentTypeError
from pyrogram.errors import ChannelPrivate, UserNotParticipant
from pyrogram.types import Chat, Message, User

from anjani import command, filters, listener, plugin, util


class SpamShield(plugin.Plugin):
    name: ClassVar[str] = "SpamShield"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection
    federation_db: util.db.AsyncCollection
    token: Optional[str]

    async def on_load(self) -> None:
        self.token = self.bot.config.get("sw_api")
        if not self.token:
            self.bot.log.warning("SpamWatch API token not exist")

        self.db = self.bot.db.get_collection("GBAN_SETTINGS")
        self.federation_db = self.bot.db.get_collection("FEDERATIONS")

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        setting = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        return {self.name: setting} if setting else {}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True)

    @listener.priority(90)
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
                await self.check(member, chat)
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
        if not chat or not user or not text or not await self.is_active(chat.id):
            return

        try:
            me, target = await util.tg.fetch_permissions(self.bot.client, chat.id, user.id)
            if not me.can_restrict_members or util.tg.is_staff_or_admin(target):
                return

            await self.check(target.user, chat)
        except (ChannelPrivate, UserNotParticipant):
            return

    async def get_ban(self, user_id: int) -> MutableMapping[str, Any]:
        if not self.token:
            return {}

        path = f"https://api.spamwat.ch/banlist/{user_id}"
        headers = {"Authorization": f"Bearer {self.token}"}
        async with self.bot.http.get(path, headers=headers) as resp:
            if resp.status in {200, 201}:
                return await resp.json()
            if resp.status == 204:
                return {}
            if resp.status == 401:
                raise ClientResponseError(
                    resp.request_info,
                    resp.history,
                    message="Make sure your Spamwatch API token is corret",
                )
            if resp.status == 403:
                raise ClientResponseError(
                    resp.request_info,
                    resp.history,
                    message="Forbidden, your token permissions is not valid",
                )
            if resp.status == 404:
                return {}
            if resp.status == 429:
                until = (await resp.json()).get("until", 0)
                raise ClientResponseError(
                    resp.request_info,
                    resp.history,
                    message=f"Too many requests. Try again in {until - datetime.now()}",
                )

            raise ClientResponseError(resp.request_info, resp.history)

    async def cas_check(self, user: User) -> Optional[str]:
        """Check on CAS"""
        retry = 0
        while True:
            try:
                async with self.bot.http.get(
                    f"https://api.cas.chat/check?user_id={user.id}"
                ) as res:
                    data = await res.json()
                    if data["ok"]:
                        reason = f"https://cas.chat/query?u={user.id}"
                        return reason

                    return None
            except (ContentTypeError, JSONDecodeError):
                if retry == 5:
                    raise

                retry += 1
                await asyncio.sleep(1)
                self.log.debug("Invalid data received from CAS server, retrying...")
            except ClientOSError:
                if retry == 10:
                    raise

                retry += 1
                await asyncio.sleep(0.5)
                self.log.debug(f"Retrying CAS check for {user.id}")

    async def is_active(self, chat_id: int) -> bool:
        """Return SpamShield setting"""
        data = await self.db.find_one({"chat_id": chat_id})
        return data["setting"] if data else True

    async def is_banned(self, user_id: int) -> bool:
        """Check if user already banned"""
        data = await self.federation_db.find_one({"_id": "AnjaniSpamShield"})
        return str(user_id) in data["banned"] if data else False

    async def ban(self, chat: Chat, user: User, reason: str) -> None:
        fullname = user.first_name + user.last_name if user.last_name else user.first_name
        await asyncio.gather(
            chat.kick_member(user.id),
            self.federation_db.update_one(
                {"_id": "AnjaniSpamShield"},
                {
                    "$set": {
                        f"banned.{user.id}": {
                            "name": fullname,
                            "reason": "Automated fban " + reason,
                            "time": datetime.now(),
                        }
                    }
                },
            ),
        )

    async def setting(self, chat_id: int, setting: bool) -> None:
        """Turn on/off SpamShield in chats"""
        await self.db.update_one({"chat_id": chat_id}, {"$set": {"setting": setting}}, upsert=True)

    async def check(self, user: User, chat: Chat) -> None:
        """Shield checker action."""
        cas, sw = await asyncio.gather(self.cas_check(user), self.get_ban(user.id))
        if not cas and not sw and not user.is_scam:
            return

        userlink = util.tg.mention(user)
        chat_link = f"[{chat.id}](https://t.me/{chat.username})" if chat.username else str(chat.id)
        reason = ""
        banner = ""
        if cas:
            banner = "[Combot Anti Spam](t.me/combot)"
            reason = f"[Link]({cas})"
        if sw:
            if not banner:
                banner = "[Spam Watch](t.me/SpamWatch)"
                reason = sw["reason"]
            else:
                banner += " & [Spam Watch](t.me/SpamWatch)"
                reason += " & " + sw["reason"]
        if user.is_scam:  # overwrite banner and reason if user is flagged by telegram
            banner = "Telegram Server"
            reason = "Flagged as a scammer."

        await asyncio.gather(
            self.bot.log_stat("banned"),
            self.ban(chat, user, reason),
            self.bot.client.send_message(
                chat.id,
                text=await self.text(chat.id, "banned-text", userlink, user.id, reason, banner),
                parse_mode="markdown",
                disable_web_page_preview=True,
            ),
            self.bot.client.send_message(
                int(self.bot.config.log_channel),
                text=(
                    "#LOG #SPAM_SHIELD\n"
                    f"**User**: {userlink}\n"
                    f"**Banned On**: {chat_link}\n"
                    f"**ID**: {user.id}\n"
                    f"**Reason**: {reason}"
                ),
                disable_web_page_preview=True,
            ),
        )

    @command.filters(filters.admin_only)
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
