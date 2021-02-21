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
import logging
import json
from typing import ClassVar, Union

import spamwatch
from motor.motor_asyncio import AsyncIOMotorCollection
from pyrogram import filters, StopPropagation
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from spamwatch.types import Ban

from anjani_bot import listener, plugin
from anjani_bot.utils import user_ban_protected

LOGGER = logging.getLogger(__name__)


class SpamShield(plugin.Plugin):
    name: ClassVar[str] = "SpamShield"

    db: AsyncIOMotorCollection
    lock: asyncio.locks.Lock
    spmwtch: str

    async def on_load(self) -> None:
        self.db = self.bot.get_collection("GBAN_SETTINGS")
        self.lock = asyncio.Lock()
        self.spmwtc = self.bot.get_config.SPAMWATCH_API

    def sw_check(self, user_id: int) -> Union[Ban, None]:
        """ Check on SpawmWatch """
        if not self.spmwtc:
            LOGGER.warning("No SpamWatch API!")
            return None
        return spamwatch.Client(self.spmwtc).get_ban(user_id)

    async def cas_check(self, user_id: int) -> Union[str, bool]:
        """ Check on CAS """
        async with self.bot.http.get(f"https://api.cas.chat/check?user_id={user_id}") as res:
            data = json.loads(await res.text())
        if data["ok"]:
            return "https://cas.chat/query?u={}".format(user_id)
        return False

    async def chat_gban(self, chat_id) -> bool:
        """ Return Spam_Shield setting """
        setting = await self.db.find_one({'chat_id': chat_id})
        return setting["setting"] if setting else True

    async def shield_pref(self, chat_id, setting: bool):
        """ Turn on/off SpamShield in chats """
        async with self.lock:
            await self.db.update_one(
                {'chat_id': chat_id},
                {
                    "$set": {'setting': setting}
                },
                upsert=True
            )

    @listener.on(filters=filters.all & filters.group, group=1, update="message")
    async def shield(self, message):
        """ Check handler """
        try:
            if(
                    await self.chat_gban(message.chat.id) and
                    (await self.bot.client.get_chat_member(message.chat.id, 'me')
                     ).can_restrict_members
            ):
                user = message.from_user
                chat = message.chat
                if user and not await user_ban_protected(self.bot.client, chat.id, user.id):
                    await self.check_and_ban(user, chat.id)
                elif message.new_chat_members:
                    for member in message.new_chat_members:
                        await self.check_and_ban(member, chat.id)
        except UserNotParticipant:
            pass

    async def check_and_ban(self, user, chat_id):
        """ Shield Check users. """
        user_id = user.id
        _cas = await self.cas_check(user_id)
        _sw = await self.sw_check(user_id)
        if _cas or _sw:
            userlink = f"[{user.first_name}](tg://user?id={user_id})"
            reason = f"[link]({_cas})" if _cas else _sw.reason
            if _cas:
                banner = "[Combot Anti Spam](t.me/combot)"
            else:
                banner = "[Spam Watch](t.me/SpamWatch)"
            text = await self.bot.text(
                chat_id,
                "banned-text",
                userlink,
                user_id,
                reason,
                banner
            )
            await asyncio.gather(
                self.bot.client.kick_chat_member(chat_id, user_id),
                self.bot.client.send_message(
                    chat_id,
                    text=text,
                    parse_mode="markdown",
                    disable_web_page_preview=True,
                ),
                self.bot.channel_log(
                    "#SPAM_SHIELD LOG\n"
                    f"**User**: {userlink} banned on {chat_id}\n"
                    f"**ID**: {user_id}\n"
                    f"**Reason**: {reason}"
                )
            )
            raise StopPropagation

    @listener.on('spamshield', admin_only=True)
    async def shield_setting(self, message):
        """ Set spamshield setting """
        chat_id = message.chat.id
        if len(message.command) >= 1:
            arg = message.command[0]
            if arg.lower() in ["on", "true", "enable"]:
                await self.shield_pref(chat_id, True)
                await message.reply_text(await self.bot.text(chat_id, "spamshield-set", "on"))
            elif arg.lower() in ["off", "false", "disable"]:
                await self.shield_pref(chat_id, False)
                await message.reply_text(await self.bot.text(chat_id, "spamshield-set", "off"))
            else:
                await message.reply_text(await self.bot.text(chat_id, "err-invalid-option"))
        else:
            setting = await self.chat_gban(message.chat.id)
            await message.reply_text(await self.bot.text(chat_id, "spamshield-view", setting))
