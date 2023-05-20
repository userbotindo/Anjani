"""Bot stats plugin"""
# Copyright (C) 2020 - 2022  UserbotIndo Team, <https://github.com/userbotindo.git>
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

from typing import ClassVar, Optional

from anjani import command, filters, plugin, util


class Topics(plugin.Plugin):
    name: ClassVar[str] = "Topic"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("CHATS")

    @command.filters(filters.can_manage_topic, aliases=["setdefaulttopic"])
    async def cmd_setactiontopic(self, ctx: command.Context) -> Optional[str]:
        """Set action topic"""
        if not ctx.chat.is_forum:
            return await self.text(ctx.chat.id, "topic-non-topic")

        await self.db.update_one(
            {"chat_id": ctx.chat.id},
            {"$set": {"action_topic": ctx.msg.message_thread_id}},
            upsert=True,
        )
        return await self.text(ctx.chat.id, "topic-set")

    # TODO: Add command to create, delete, edit topic
