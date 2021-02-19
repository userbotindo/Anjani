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
from pyrogram import filters, StopPropagation
from spamwatch.types import Ban

from .. import anjani, plugin, Config, pool
from ..utils import user_ban_protected

LOGGER = logging.getLogger(__name__)


class SpamCheck:
    lock = asyncio.Lock()
    spmwtc = Config.SPAMWATCH_API
    shield_db = anjani.get_collection("GBAN_SETTINGS")

    @classmethod
    @pool.run_in_thread
    def sw_check(cls, user_id: int) -> Union[Ban, None]:
        """ Check on SpawmWatch """
        if not cls.spmwtc:
            LOGGER.warning("No SpamWatch API!")
            return None
        return spamwatch.Client(cls.spmwtc).get_ban(user_id)

    @staticmethod
    async def cas_check(user_id: int) -> Union[str, bool]:
        """ Check on CAS """
        async with anjani.http.get(f"https://api.cas.chat/check?user_id={user_id}") as res:
            data = json.loads(await res.text())
        if data["ok"]:
            return "https://cas.chat/query?u={}".format(user_id)
        return False

    @classmethod
    async def chat_gban(cls, chat_id) -> bool:
        """ Return Spam_Shield setting """
        setting = await cls.shield_db.find_one({'chat_id': chat_id})
        return setting["setting"] if setting else True

    @classmethod
    async def shield_pref(cls, chat_id, setting: bool):
        """ Turn on/off SpamShield in chats """
        async with cls.lock:
            await cls.shield_db.update_one(
                {'chat_id': chat_id},
                {
                    "$set": {'setting': setting}
                },
                upsert=True
            )


class SpamShield(plugin.Plugin, SpamCheck):
    name: ClassVar[str] = "SpamShield"

    @anjani.on_message(filters.all & filters.group, group=1)
    async def shield(self, message):
        """ Check handler """
        if(
                await SpamShield.chat_gban(message.chat.id) and
                (await self.get_chat_member(message.chat.id, 'me')).can_restrict_members
        ):
            user = message.from_user
            chat = message.chat
            if user and not await user_ban_protected(self, chat.id, user.id):
                await SpamShield.check_and_ban(self, user, chat.id)
            elif message.new_chat_members:
                for member in message.new_chat_members:
                    await SpamShield.check_and_ban(self, member, chat.id)

    async def check_and_ban(self, user, chat_id):
        """ Shield Check users. """
        user_id = user.id
        _cas = await SpamShield.cas_check(user_id)
        _sw = await SpamShield.sw_check(user_id)
        if _cas or _sw:
            userlink = f"[{user.first_name}](tg://user?id={user_id})"
            reason = f"[link]({_cas})" if _cas else _sw.reason
            if _cas:
                banner = "[Combot Anti Spam](t.me/combot)"
            else:
                banner = "[Spam Watch](t.me/SpamWatch)"
            text = await self.text(
                chat_id,
                "banned-text",
                userlink,
                user_id,
                reason,
                banner
            )
            await asyncio.gather(
                self.kick_chat_member(chat_id, user_id),
                self.send_message(
                    chat_id,
                    text=text,
                    parse_mode="markdown",
                    disable_web_page_preview=True,
                ),
                self.channel_log(
                    "#SPAM_SHIELD LOG\n"
                    f"**User**: {userlink} banned on {chat_id}\n"
                    f"**ID**: {user_id}\n"
                    f"**Reason**: {reason}"
                )
            )
            raise StopPropagation


    @anjani.on_command('spamshield', admin_only=True)
    async def shield_setting(self, message):
        """ Set spamshield setting """
        chat_id = message.chat.id
        if len(message.command) >= 1:
            arg = message.command[0]
            if arg.lower() in ["on", "true", "enable"]:
                await SpamShield.shield_pref(chat_id, True)
                await message.reply_text(await self.text(chat_id, "spamshield-set", "on"))
            elif arg.lower() in ["off", "false", "disable"]:
                await SpamShield.shield_pref(chat_id, False)
                await message.reply_text(await self.text(chat_id, "spamshield-set", "off"))
            else:
                await message.reply_text(await self.text(chat_id, "err-invalid-option"))
        else:
            setting = await SpamShield.chat_gban(message.chat.id)
            await message.reply_text(await self.text(chat_id, "spamshield-view", setting))
