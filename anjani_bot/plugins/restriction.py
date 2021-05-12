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

from typing import ClassVar

from pyrogram.errors import PeerIdInvalid, UserNotParticipant

from anjani_bot import listener, plugin
from anjani_bot.utils import (
    ParsedChatMember,
    extract_user,
    extract_user_and_text,
    user_ban_protected,
)


class Restrictions(plugin.Plugin):
    name: ClassVar[str] = "Restriction"
    helpable: ClassVar[bool] = True

    async def parse_member(self, user_ids) -> ParsedChatMember:
        """Get member atrribute"""
        member = await extract_user(self.bot.client, user_ids)
        return ParsedChatMember(member)

    @listener.on("kick", can_restrict=True)
    async def kick_member(self, message):
        """Kick chat member"""
        user, _ = extract_user_and_text(message)
        chat_id = message.chat.id
        if user is None:
            return await message.reply_text(await self.bot.text(chat_id, "no-kick-user"))
        try:
            if await user_ban_protected(self.bot, chat_id, user):
                return await message.reply_text(await self.bot.text(chat_id, "admin-kick"))
        except UserNotParticipant:
            return await message.reply_text(await self.bot.text(chat_id, "err-not-participant"))
        await message.chat.kick_member(user)
        kicked = await self.parse_member(user)
        await message.reply_text(await self.bot.text(chat_id, "kick-done", kicked.first_name))
        await message.chat.unban_member(user)

    @listener.on("ban", can_restrict=True)
    async def ban_member(self, message):
        """Ban chat member"""
        user, _ = extract_user_and_text(message)
        chat_id = message.chat.id
        if user is None:
            return await message.reply_text(await self.bot.text(chat_id, "no-ban-user"))
        try:
            if await user_ban_protected(self.bot, chat_id, user):
                return await message.reply_text(await self.bot.text(chat_id, "admin-ban"))
        except UserNotParticipant:
            return await message.reply_text(await self.bot.text(chat_id, "err-not-participant"))
        await message.chat.kick_member(user)
        banned = await self.parse_member(user)
        await message.reply_text(await self.bot.text(chat_id, "ban-done", banned.first_name))

    @listener.on("unban", can_restrict=True)
    async def unban_member(self, message):
        """Unban chat member"""
        (
            user,
            _,
        ) = extract_user_and_text(message)
        if user is None:
            return await message.reply_text(await self.bot.text(message.chat.id, "unban-no-user"))
        try:
            await message.chat.unban_member(user)
        except PeerIdInvalid:
            return await message.reply_text(
                await self.bot.text(message.chat.id, "err-peer-invalid")
            )
        unbanned = await self.parse_member(user)
        await message.reply_text(
            await self.bot.text(message.chat.id, "unban-done", unbanned.first_name)
        )
