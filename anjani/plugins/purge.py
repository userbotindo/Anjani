""" Message purging plugin. """
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

from datetime import datetime
from typing import ClassVar, Optional

from pyrogram.errors import MessageDeleteForbidden

from anjani import command, filters, plugin


class Purges(plugin.Plugin):
    name: ClassVar[str] = "Purges"
    helpable: ClassVar[bool] = True

    @command.filters(filters.can_delete)
    async def cmd_del(self, ctx: command.Context) -> Optional[str]:
        """Delete replied message"""
        reply_msg = ctx.msg.reply_to_message
        if not reply_msg:
            return await self.text(ctx.chat.id, "error-reply-to-message")

        await self.bot.client.delete_messages(ctx.chat.id, [reply_msg.id, ctx.msg.id])
        return None

    @command.filters(filters.can_delete, aliases=["prune"])
    async def cmd_purge(self, ctx: command.Context) -> Optional[str]:
        """purge message from message replied"""
        if not ctx.msg.reply_to_message:
            return await self.text(ctx.chat.id, "error-reply-to-message")

        time_start = datetime.now()
        start, end = ctx.msg.reply_to_message.id, ctx.msg.id
        messages = [*range(start, end)]

        try:
            await self.bot.client.delete_messages(chat_id=ctx.chat.id, message_ids=messages)
        except MessageDeleteForbidden:
            await ctx.respond(await self.text(ctx.chat.id, "purge-error", delete_after=5))
            return None
        else:
            await ctx.msg.delete()

        time_end = datetime.now()
        run_time = (time_end - time_start).seconds

        await ctx.respond(
            await self.text(ctx.chat.id, "purge-done", len(messages), run_time), delete_after=5
        )
        return None
