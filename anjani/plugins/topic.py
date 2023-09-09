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

from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from anjani import command, filters, listener, plugin, util


class Topics(plugin.Plugin):
    name: ClassVar[str] = "Topic"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("CHATS")

    @listener.filters(filters.regex(r"topic_action_(.*)"))
    async def on_callback_query(self, query: CallbackQuery) -> None:
        action = query.matches[0].group(1)
        chat = query.message.chat

        user = await chat.get_member(query.from_user.id)
        if not user.privileges or not user.privileges.can_manage_topics:
            await query.answer(await self.text(chat.id, "error-no-rights"))
            return

        if action == "cancel":
            await query.message.delete()
            return
        if action == "remove":
            await self.bot.client.delete_forum_topic(chat.id, query.message.message_thread_id)
            return

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

    @command.filters(filters.can_manage_topic)
    async def cmd_actiontopic(self, ctx: command.Context) -> Optional[str]:
        """Get action topic"""
        if not ctx.chat.is_forum:
            return await self.text(ctx.chat.id, "topic-non-topic")

        chat_id = ctx.chat.id
        chat = await self.db.find_one({"chat_id": ctx.chat.id})
        if not chat or not chat.get("action_topic"):
            return await self.text(ctx.chat.id, "topic-action-general")

        return await self.text(
            ctx.chat.id,
            "topic-action-custom",
            f"t.me/c/{str(chat_id).replace('-100', '')}/{chat['action_topic']}",
        )

    @command.filters(filters.can_manage_topic, aliases=["newtopic"])
    async def cmd_createtopic(self, ctx: command.Context, name: Optional[str]) -> Optional[str]:
        """create topic"""
        if not ctx.chat.is_forum:
            return await self.text(ctx.chat.id, "topic-non-topic")

        if not name:
            return await self.text(ctx.chat.id, "topic-name-missing")

        await self.bot.client.create_forum_topic(ctx.chat.id, name)
        return await self.text(ctx.chat.id, "topic-created", name)

    @command.filters(filters.can_manage_topic)
    async def cmd_renametopic(self, ctx: command.Context, name: Optional[str]) -> Optional[str]:
        """Remove topic"""
        if not ctx.chat.is_forum:
            return await self.text(ctx.chat.id, "topic-non-topic")

        if not name:
            return await self.text(ctx.chat.id, "topic-name-missing")

        await self.bot.client.edit_forum_topic(ctx.chat.id, ctx.msg.message_thread_id, name)
        return await self.text(ctx.chat.id, "topic-renamed", name)

    @command.filters(filters.can_manage_topic)
    async def cmd_opentopic(self, ctx: command.Context) -> Optional[str]:
        """Open topic"""
        if not ctx.chat.is_forum:
            return await self.text(ctx.chat.id, "topic-non-topic")

        await self.bot.client.reopen_forum_topic(ctx.chat.id, ctx.msg.message_thread_id)
        return await self.text(ctx.chat.id, "topic-reopened", delete_after=3)

    @command.filters(filters.can_manage_topic)
    async def cmd_closetopic(self, ctx: command.Context) -> Optional[str]:
        if not ctx.chat.is_forum:
            return await self.text(ctx.chat.id, "topic-non-topic")

        await ctx.respond(await self.text(ctx.chat.id, "topic-closing"), delete_after=3)
        await self.bot.client.close_forum_topic(ctx.chat.id, ctx.msg.message_thread_id)

    @command.filters(filters.can_manage_topic, aliases=["removetopic"])
    async def cmd_deletetopic(self, ctx: command.Context) -> Optional[str]:
        """Remove topic"""
        if not ctx.chat.is_forum:
            return await self.text(ctx.chat.id, "topic-non-topic")

        await ctx.respond(
            await self.text(ctx.chat.id, "topic-remove-confirm"),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="⚠️ Delete",
                            callback_data="topic_action_remove",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="Cancel",
                            callback_data="topic_action_cancel",
                        )
                    ],
                ]
            ),
        )
