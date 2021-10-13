""" Restriction Plugin. """
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
from typing import ClassVar, Optional

from pyrogram.errors import PeerIdInvalid, UserNotParticipant
from pyrogram.types import User

from anjani import command, filters, plugin, util


class Restrictions(plugin.Plugin):
    name: ClassVar[str] = "Restriction"
    helpable: ClassVar[bool] = True

    @command.filters(filters.can_restrict)
    async def cmd_kick(
        self, ctx: command.Context, user: Optional[User] = None, *, reason: str = ""
    ) -> str:
        """Kick chat member"""
        chat = ctx.chat

        if not user:
            if ctx.args and not ctx.msg.reply_to_message:
                return await self.text(chat.id, "no-kick-user")
            user = ctx.msg.reply_to_message.from_user
            reason = ctx.input

        try:
            target = await chat.get_member(user.id)
            if util.tg.is_staff_or_admin(target, self.bot.staff):
                return await self.text(chat.id, "admin-kick")
        except UserNotParticipant:
            return await self.text(chat.id, "err-not-participant")

        await chat.kick_member(user.id)
        ret = await self.text(chat.id, "kick-done", user.first_name)
        await chat.unban_member(user.id)

        if reason:
            ret += await self.text(chat.id, "kick-reason", reason)
        return ret

    @command.filters(filters.can_restrict)
    async def cmd_ban(
        self, ctx: command.Context, user: Optional[User] = None, *, reason: str = ""
    ) -> str:
        """Ban chat member"""
        chat = ctx.chat

        if not user:
            if ctx.args and not ctx.msg.reply_to_message:
                return await self.text(chat.id, "no-ban-user")
            user = ctx.msg.reply_to_message.from_user
            reason = ctx.input

        try:
            target = await chat.get_member(user.id)
            if util.tg.is_staff_or_admin(target, self.bot.staff):
                return await self.text(chat.id, "admin-ban")
        except UserNotParticipant:
            return await self.text(chat.id, "err-not-participant")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "ban-done", user.first_name), chat.kick_member(user.id)
        )
        if reason:
            ret += await self.text(chat.id, "ban-reason", reason)

        return ret

    @command.filters(filters.can_restrict)
    async def cmd_unban(self, ctx: command.Context, user: Optional[User] = None) -> str:
        """Unban chat member"""
        chat = ctx.chat

        if not user:
            if ctx.args and not ctx.msg.reply_to_message:
                return await self.text(chat.id, "unban-no-user")
            user = ctx.msg.reply_to_message.from_user

        try:
            await chat.unban_member(user.id)
        except PeerIdInvalid:
            return await self.text(chat.id, "err-peer-invalid")

        return await self.text(chat.id, "unban-done", user.first_name)
