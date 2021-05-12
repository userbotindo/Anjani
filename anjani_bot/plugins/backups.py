"""Main bot commands"""
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
import json
import os
from datetime import datetime
from typing import ClassVar

from pyrogram import filters

from anjani_bot import listener, plugin


class Backups(plugin.Plugin):
    name: ClassVar[str] = "Backups"
    helpable: ClassVar[bool] = True

    @listener.on("backup", filters.group, admin_only=True)
    async def backup_data(self, message):
        """Backup chat data from file"""
        chat_id = message.chat.id
        msg = await message.reply_text(await self.bot.text(chat_id, "backup-progress"))
        chat_name = message.chat.title
        data = await self.bot.backup_plugin_data(chat_id)
        if len(data.keys()) <= 1:
            return await msg.edit_text(await self.bot.text(chat_id, "backup-null"))
        string = json.dumps(data, indent=2)
        file_name = f"{chat_name}-backup.anjani"
        with open(file_name, "w") as file:
            file.write(string)
        saved = ""
        del data["chat_id"]
        for key, _ in data.items():
            saved += f"\n× `{key}`"
        date = datetime.now().strftime("%H:%M - %d/%b/%Y")
        await asyncio.gather(
            message.reply_document(
                file_name,
                caption=await self.bot.text(chat_id, "backup-doc", chat_name, chat_id, date, saved),
            ),
            msg.delete(),
            self.bot.channel_log(
                "**Successfully backing-up:**\n"
                f"Chat: `{chat_name}`\n"
                f"Chat ID: `{chat_id}`\n"
                f"Time: `{date}`\n\n"
                f"**Backed-up Data:** {saved}"
            ),
        )
        os.remove(file_name)

    @listener.on("restore", filters.group, admin_only=True)
    async def restore_data(self, message):
        """Restore data to a file"""
        chat_id = message.chat.id
        if not (message.reply_to_message or message.reply_to_message.document):
            return await message.reply_text(await self.bot.text(chat_id, "no-backup-file"))
        msg = await message.reply_text(await self.bot.text(chat_id, "restore-progress"))
        data = await message.reply_to_message.download(self.bot.get_config.download_path)
        with open(data, "r") as file:
            text = file.read()
        parsed_data = json.loads(text)
        try:  # also check if the file isn't a valid backup file
            if parsed_data["chat_id"] != chat_id:
                return await msg.edit(await self.bot.text(chat_id, "backup-id-invalid"))
        except KeyError:
            return await msg.edit(await self.bot.text(chat_id, "invalid-backup-file"))
        if len(parsed_data.keys()) == 1:
            return await msg.edit(await self.bot.text(chat_id, "backup-data-null"))
        await self.bot.backup_plugin_data(chat_id, parsed_data)
        await asyncio.gather(
            msg.edit(await self.bot.text(chat_id, "backup-done")),
            self.bot.channel_log(
                "**Successfully restored:**\n"
                f"Chat: `{message.chat.title}`\n"
                f"Chat ID: `{message.chat.id}`"
            ),
        )
        os.remove(data)
