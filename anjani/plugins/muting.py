"""Member muting plugin"""
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
from datetime import datetime
from typing import ClassVar, Optional

from pyrogram.errors import PeerIdInvalid, UsernameInvalid, UsernameNotOccupied
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.types import ChatMember, ChatPermissions, Message, User

from anjani import command, filters, plugin, util


class Muting(plugin.Plugin):
    name: ClassVar[str] = "Muting"
    helpable: ClassVar[bool] = True

    async def _muter(self, message: Message, user: User, time: int = 0, flag: str = "") -> str:
        chat_id = message.chat.id
        user_id = user.id
        mstring = "mute-success-time" if time else "mute-success"
        try:
            await self.bot.client.restrict_chat_member(
                chat_id, user_id, ChatPermissions(), datetime.fromtimestamp(time)
            )

            return await self.text(chat_id, mstring, user.first_name, flag)
        except (UsernameInvalid, UsernameNotOccupied, PeerIdInvalid):
            return await self.text(chat_id, "err-invalid-username-id")

    @command.filters(filters.can_restrict)
    async def cmd_mute(
        self, ctx: command.Context, member: Optional[ChatMember] = None, flag: str = ""
    ) -> str:
        """Mute Chat Member"""
        chat_id = ctx.chat.id
        user = None

        if not member:
            if ctx.args and not ctx.args[0].endswith(("s", "m", "h")):
                return await self.text(chat_id, "no-mute-user")

            if ctx.msg.reply_to_message and ctx.msg.reply_to_message.from_user:
                try:
                    member = await self.bot.client.get_chat_member(
                        chat_id, ctx.msg.reply_to_message.from_user.id
                    )
                except UserNotParticipant:
                    # User is not a participant in the chat (replying from channel discussion)
                    user = await self.bot.client.get_users(ctx.msg.reply_to_message.from_user.id)
                    if isinstance(user, list):
                        user = user[0]

                flag = ctx.args[0] if ctx.args else ""
            else:
                return await self.text(chat_id, "no-mute-user")

        if member is not None:
            user = member.user
            if util.tg.is_staff_or_admin(member):
                return await self.text(chat_id, "cant-mute-admin")

            if member.permissions and not member.permissions.can_send_messages:
                return await self.text(chat_id, "already-muted")

        if not user:
            return await self.text(chat_id, "no-mute-user")

        if user.id == self.bot.uid:
            return await self.text(chat_id, "self-muting")

        if util.tg.is_staff(user.id):
            return await self.text(chat_id, "cant-mute-admin")

        if flag:
            until = util.time.extract_time(flag)
            if not until:
                return await self.text(chat_id, "invalid-time-flag")
        else:
            until = 0

        return await self._muter(ctx.msg, user, until, flag)

    @command.filters(filters.can_restrict)
    async def cmd_unmute(self, ctx: command.Context, member: Optional[ChatMember] = None) -> str:
        """Unmute chat member"""
        chat_id = ctx.chat.id
        if member is None:
            if ctx.args:
                return await self.text(chat_id, "err-peer-invalid")

            if ctx.msg.reply_to_message and ctx.msg.reply_to_message.from_user:
                member = await self.bot.client.get_chat_member(
                    chat_id, ctx.msg.reply_to_message.from_user.id
                )
            else:
                return await self.text(chat_id, "no-unmute-user")

        if member.permissions and not member.permissions.can_send_messages:
            _, t = await asyncio.gather(
                ctx.message.chat.unban_member(member.user.id),
                self.text(chat_id, "unmute-done")
            )
            return t

        return await self.text(chat_id, "user-not-muted")
