""" Admin Plugin, Can manage your Group. """
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
from typing import ClassVar, Optional

from pyrogram.errors import (
    ChatAdminRequired,
    FloodWait,
    MessageDeleteForbidden,
    PeerIdInvalid,
    UserAdminInvalid,
    UserIdInvalid,
    UserNotParticipant
)
from pyrogram.types import ChatMember, User

from anjani import command, filters, plugin, util


class Admins(plugin.Plugin):
    name: ClassVar[str] = "Admins"
    helpable: ClassVar[bool] = True

    @command.filters(filters.can_pin)
    async def cmd_pin(self, ctx: command.Context) -> Optional[str]:
        """Pin message on chats"""
        if not ctx.msg.reply_to_message:
            return await self.text(ctx.msg.chat.id, "error-reply-to-message")

        is_silent = True
        if ctx.input and ctx.input in {
            "notify",
            "loud",
            "violence",
        }:
            is_silent = False
        await ctx.msg.reply_to_message.pin(disable_notification=is_silent)

    @command.filters(filters.can_pin)
    async def cmd_unpin(self, ctx: command.Context) -> None:
        """Unpin message on chats"""
        chat = ctx.msg.chat

        if ctx.input and ctx.input == "all":
            await self.bot.client.unpin_all_chat_messages(chat.id)
        elif not ctx.msg.reply_to_message:
            pinned = chat.pinned_message.message_id
            await self.bot.client.unpin_chat_message(chat.id, pinned)
        else:
            await ctx.msg.reply_to_message.unpin()

    @command.filters(filters.can_change_info)
    async def cmd_setgpic(self, ctx: command.Context) -> Optional[str]:
        """Set group picture"""
        msg = ctx.msg.reply_to_message or ctx.msg
        file = msg.photo or None

        if not file:
            return await self.text(msg.chat.id, "gpic-no-photo")
        
        await self.bot.client.set_chat_photo(msg.chat.id, photo=file.file_id)

    async def cmd_adminlist(self, ctx: command.Context) -> str:
        """Get list of chat admins"""
        chat = ctx.msg.chat
        admins = ""

        member: ChatMember
        async for member in self.bot.client.iter_chat_members(chat.id, filter="administrators"):  # type: ignore
            # Pyrogram is weird it returns all members even tho we provided the filter
            if member.status == "administrator":
                name = (member.user.first_name + " " + member.user.last_name
                        ) if member.user.last_name else member.user.first_name
                admins += f"• [{name}](tg://user?id={member.user.id})\n"

        return admins

    @command.filters(filters.can_restrict)
    async def cmd_zombies(self, ctx: command.Context) -> str:
        """Kick all deleted acc in group."""
        chat = ctx.msg.chat
        zombie = 0

        await ctx.respond(await self.text(chat.id, "finding-zombie"))
        async for member in self.bot.client.iter_chat_members(chat.id):  # type: ignore
            if member.user.is_deleted:
                zombie += 1
                try:
                    await self.bot.client.kick_chat_member(chat.id, member.user.id)
                except UserAdminInvalid:
                    zombie -= 1
                except FloodWait as flood:
                    await asyncio.sleep(flood.x)  # type: ignore

        if zombie == 0:
            return await self.text(chat.id, "zombie-clean")

        return await self.text(chat.id, "cleaning-zombie", zombie)

    @command.filters(filters.can_promote)
    async def cmd_promote(self, ctx: command.Context, user: User) -> str:
        """Bot promote member, required Both permission of can_promote"""
        chat = ctx.msg.chat

        if not isinstance(user, User):
            return await self.text(chat.id, "err-peer-invalid")
        if user.id == ctx.author.id and ctx.args:
            return await self.text(chat.id, "promote-error-self")
        if user.id == ctx.author.id:
            return await self.text(chat.id, "no-promote-user")

        if user.id == self.bot.uid:
            return await self.text(chat.id, "error-its-myself")

        # use cached permissions from filters
        bot, _ = await util.tg.fetch_permissions(self.bot.client, chat.id, user.id)
        try:
            await chat.promote_member(
                user_id=user.id,
                can_change_info=bot.can_change_info,
                can_post_messages=bot.can_post_messages,
                can_edit_messages=bot.can_edit_messages,
                can_delete_messages=bot.can_delete_messages,
                can_restrict_members=bot.can_restrict_members,
                can_promote_members=bot.can_promote_members,
                can_invite_users=bot.can_invite_users,
                can_pin_messages=bot.can_pin_messages,
            )
        except ChatAdminRequired:
            return await self.text(chat.id, "promote-error-perm")
        except UserIdInvalid:
            return await self.text(chat.id, "promote-error-invalid")

        return await self.text(chat.id, "promote-success")

    @command.filters(filters.can_promote)
    async def cmd_demote(self, ctx: command.Context, user: User) -> str:
        """Demoter Just owner and promoter can demote admin."""
        chat = ctx.msg.chat

        if not isinstance(user, User):
            return await self.text(chat.id, "err-peer-invalid")
        if user.id == ctx.author.id and ctx.args:
            return await self.text(chat.id, "demote-error-self")
        if user.id == ctx.author.id:
            return await self.text(chat.id, "no-demote-user")

        if user.id == self.bot.uid:
            return await self.text(chat.id, "error-its-myself")

        try:
            await chat.promote_member(
                user_id=user.id,
                can_change_info=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_delete_messages=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_invite_users=False,
                can_pin_messages=False,
            )
        except ChatAdminRequired:
            return await self.text(chat.id, "demote-error-perm")

        return await self.text(chat.id, "demote-success")

    @command.filters(filters.can_delete)
    async def cmd_del(self, ctx: command.Context) -> Optional[str]:
        """Delete replied message"""
        if not ctx.msg.reply_to_message:
            return await self.text(ctx.chat.id, "error-reply-to-message")

        await asyncio.gather(ctx.msg.reply_to_message.delete(),
                             ctx.msg.delete())

    @command.filters(filters.can_delete)
    async def cmd_purge(self, ctx: command.Context) -> Optional[str]:
        """purge message from message replied"""
        if not ctx.msg.reply_to_message:
            return await self.text(ctx.msg.chat.id, "error-reply-to-message")

        time_start = datetime.now()
        start, end = ctx.msg.reply_to_message.message_id, ctx.msg.message_id
        messages = [*range(start, end)]

        try:
            await self.bot.client.delete_messages(chat_id=ctx.chat.id,
                                                  message_ids=messages)
        except MessageDeleteForbidden:
            await ctx.respond(await self.text(ctx.chat.id, "purge-error", delete_after=5))
            return
        else:
            await ctx.msg.delete()

        time_end = datetime.now()
        run_time = (time_end - time_start).seconds

        await ctx.respond(await self.text(ctx.chat.id, "purge-done", len(messages), run_time), 
                          delete_after=5)

    @command.filters(filters.can_restrict)
    async def cmd_kick(self, ctx: command.Context, user: Optional[User] = None) -> str:
        """Kick chat member"""
        chat = ctx.chat

        if not user:
            return await self.text(chat.id, "no-kick-user")

        try:
            target = await chat.get_member(user.id)
            if util.tg.is_staff_or_admin(target, self.bot.staff):
                return await self.text(chat.id, "admin-kick")
        except UserNotParticipant:
            return await self.text(chat.id, "err-not-participant")

        await chat.kick_member(user.id)
        ret, _ = await asyncio.gather(self.text(chat.id, "kick-done", user.first_name),
                                      chat.unban_member(user.id))

        return ret

    @command.filters(filters.can_restrict)
    async def cmd_ban(self, ctx: command.Context, user: Optional[User] = None) -> str:
        """Ban chat member"""
        chat = ctx.chat

        if not user:
            return await self.text(chat.id, "no-ban-user")

        try:
            target = await chat.get_member(user.id)
            if util.tg.is_staff_or_admin(target, self.bot.staff):
                return await self.text(chat.id, "admin-ban")
        except UserNotParticipant:
            return await self.text(chat.id, "err-not-participant")

        ret, _ = await asyncio.gather(self.text(chat.id, "ban-done", user.first_name),
                                      chat.kick_member(user.id))

        return ret

    @command.filters(filters.can_restrict)
    async def cmd_unban(self, ctx: command.Context, user: Optional[User] = None) -> str:
        """Unban chat member"""
        chat = ctx.chat

        if not user:
            return await self.text(chat.id, "unban-no-user")

        try:
            await chat.unban_member(user.id)
        except PeerIdInvalid:
            return await self.text(chat.id, "err-peer-invalid")

        return await self.text(chat.id, "unban-done", user.first_name)
