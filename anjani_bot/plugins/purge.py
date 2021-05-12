""" Purging message plugin. """
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
from typing import ClassVar

from anjani_bot import listener, plugin


class Purges(plugin.Plugin):
    name: ClassVar[str] = "Purges"
    helpable: ClassVar[bool] = True

    @listener.on("del", can_delete=True)
    async def del_message(self, message):
        """Delete replied message"""
        if message.reply_to_message:
            await message.reply_to_message.delete()
            await message.delete()
        else:
            await message.reply_text(await self.bot.text(message.chat.id, "error-reply-to-message"))

    @listener.on(["purge", "prune"], can_delete=True)
    async def purge_message(self, message):
        """purge message from message replied"""
        if not message.reply_to_message:
            return await message.reply_text(
                await self.bot.text(message.chat.id, "error-reply-to-message")
            )

        time_start = datetime.now()
        await message.delete()
        message_ids = []
        purged = 0
        for msg_id in range(message.reply_to_message.message_id, message.message_id):
            message_ids.append(msg_id)
            if len(message_ids) == 100:
                await self.bot.client.delete_messages(
                    chat_id=message.chat.id,
                    message_ids=message_ids,
                    revoke=True,
                )
                purged += len(message_ids)
                message_ids = []
        if message_ids:
            await self.bot.client.delete_messages(
                chat_id=message.chat.id,
                message_ids=message_ids,
                revoke=True,
            )
            purged += len(message_ids)
        time_end = datetime.now()
        run_time = (time_end - time_start).seconds
        _msg = await self.bot.client.send_message(
            message.chat.id,
            await self.bot.text(message.chat.id, "purge-done", purged, run_time),
        )
        await asyncio.sleep(5)
        await _msg.delete()
