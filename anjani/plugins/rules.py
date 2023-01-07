"""Bot rules command"""
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
from typing import Any, MutableMapping, Optional

from pyrogram.errors import PeerIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from anjani import command, filters, plugin, util


class Rules(plugin.Plugin):
    name = "Rules"
    helpable = True

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("RULES")

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        rules = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        return {self.name: rules} if rules else {}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True)

    @command.filters(filters.admin_only)
    async def cmd_setrules(self, ctx: command.Context) -> str:
        chat = ctx.chat
        if not ctx.input_raw:
            return await self.text(chat.id, "rules-blank-err")

        content = ctx.input_raw
        ret, _ = await asyncio.gather(
            self.text(chat.id, "rules-set", f"t.me/{self.bot.user.username}?start=rules_{chat.id}"),
            self.db.update_one({"chat_id": chat.id}, {"$set": {"rules": content}}, upsert=True),
        )
        return ret

    @command.filters(filters.admin_only)
    async def cmd_clearrules(self, ctx: command.Context) -> str:
        chat = ctx.chat
        ret, _ = await asyncio.gather(
            self.text(chat.id, "rules-clear"), self.db.delete_one({"chat_id": chat.id})
        )
        return ret

    async def cmd_rules(self, ctx: command.Context) -> Optional[str]:
        chat = ctx.chat
        content = await self.db.find_one({"chat_id": chat.id})
        if not content:
            return await self.text(chat.id, "rules-none")

        await ctx.respond(
            await self.text(chat.id, "rules-view-caption"),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=await self.text(chat.id, "rules-button"),
                            url=f"t.me/{self.bot.user.username}?start=rules_{chat.id}",
                        )
                    ]
                ]
            ),
        )
        return None

    async def start_rules(self, ctx: command.Context) -> str:
        try:
            rules_id = int(ctx.input.split("_")[1])
        except ValueError:
            return await self.text(ctx.chat.id, "rules-invalid-button", ctx.input.split("_")[1])
        try:
            content, chat = await asyncio.gather(
                self.db.find_one({"chat_id": rules_id}),
                self.bot.client.get_chat(rules_id),
            )
        except PeerIdInvalid:
            content, chat = None, None

        if not content or not chat:
            return await self.text(rules_id, "rules-none")

        text = await self.text(rules_id, "rules-view-pm", chat.title)

        return text + content["rules"]
