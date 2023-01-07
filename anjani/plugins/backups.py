"""Plugin Backup and Restore"""
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
import json
from datetime import datetime
from typing import Any, ClassVar, MutableMapping, Optional

from aiopath import AsyncPath

from anjani import command, filters, plugin


class Backups(plugin.Plugin):
    name: ClassVar[str] = "Backups"
    helpable: ClassVar[bool] = True

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("MIGRATED_BACKUPS")

    @command.filters(filters.admin_only)
    async def cmd_backup(self, ctx: command.Context) -> Optional[str]:
        """Backup chat data from file"""
        chat = ctx.chat
        data = {"chat_id": chat.id}
        file = AsyncPath(f"{chat.title}-backup.anjani")

        await ctx.respond(await self.text(chat.id, "backup-progress"))

        results = await self.bot.dispatch_event("plugin_backup", chat.id)
        if not results or len(results) <= 1:
            return await self.text(chat.id, "backup-null")

        result: MutableMapping[str, Any]
        for result in results:
            data.update(result)

        await file.write_text(json.dumps(data, indent=2))

        saved = ""
        del data["chat_id"]
        for key in data:
            saved += f"\n× `{key}`"

        date = datetime.now().strftime("%H:%M - %d/%b/%Y")
        await asyncio.gather(
            ctx.msg.reply_document(
                str(file),
                caption=await self.text(chat.id, "backup-doc", chat.title, chat.id, date, saved),
            ),
            ctx.response.delete(),
        )
        await file.unlink()

        return None

    @command.filters(filters.admin_only)
    async def cmd_restore(self, ctx: command.Context) -> Optional[str]:
        """Restore data to a file"""
        chat = ctx.chat
        reply_msg = ctx.msg.reply_to_message

        if not reply_msg or (reply_msg and not reply_msg.document):
            return await self.text(chat.id, "no-backup-file")

        await ctx.respond(await self.text(chat.id, "restore-progress"))

        file = AsyncPath(await ctx.msg.reply_to_message.download())

        try:
            data: MutableMapping[str, Any] = json.loads(await file.read_text())
        except json.JSONDecodeError:
            return await self.text(chat.id, "invalid-backup-file")

        try:  # also check if the file isn't a valid backup file
            if data["chat_id"] != chat.id:
                return await self.text(chat.id, "backup-id-invalid")
        except KeyError:
            return await self.text(chat.id, "invalid-backup-file")

        if len(data) <= 1:
            return await self.text(chat.id, "backup-data-null")

        if data.get("_migrated", False):
            await ctx.respond(
                await self.text(chat.id, "restore-progress") + "\nMigrate file detected..."
            )
            await self.db.insert_one({"chat_id": chat.id, "on": datetime.now()})

        await self.bot.dispatch_event("plugin_restore", chat.id, data)
        await asyncio.gather(ctx.respond(await self.text(chat.id, "backup-done")), file.unlink())
        return None
