""" Admin Plugin, Can manage your Group. """
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
from typing import ClassVar, Optional

from pyrogram.enums.chat_member_status import ChatMemberStatus
from pyrogram.enums.chat_type import ChatType
from pyrogram.errors import (
    BotChannelsNa,
    ChatAdminRequired,
    FloodWait,
    UserAdminInvalid,
    UserCreator,
    UserIdInvalid,
    UserPrivacyRestricted,
)
from pyrogram.types import Chat, ChatPrivileges, User

from anjani import command, filters, plugin, util


class Admins(plugin.Plugin):
    name: ClassVar[str] = "Admins"
    helpable: ClassVar[bool] = True

    @command.filters(filters.can_pin)
    async def cmd_pin(self, ctx: command.Context) -> Optional[str]:
        """Pin message on chats"""
        if not ctx.msg.reply_to_message:
            return await self.text(ctx.chat.id, "error-reply-to-message")

        is_silent = True
        if ctx.input and ctx.input in {
            "notify",
            "loud",
            "violence",
        }:
            is_silent = False

        await ctx.msg.reply_to_message.pin(disable_notification=is_silent)
        return None

    @command.filters(filters.can_pin)
    async def cmd_unpin(self, ctx: command.Context) -> Optional[str]:
        """Unpin message on chats"""
        chat = ctx.chat

        if ctx.input and ctx.input == "all":
            await self.bot.client.unpin_all_chat_messages(chat.id)
        elif not ctx.msg.reply_to_message:
            chat = await self.bot.client.get_chat(chat.id)
            if not isinstance(chat, Chat):
                raise ValueError("Invalid Chat")

            if not chat.pinned_message:
                return await self.text(chat.id, "no-pinned-message")

            pinned = chat.pinned_message.id
            await self.bot.client.unpin_chat_message(chat.id, pinned)
        else:
            await ctx.msg.reply_to_message.unpin()

        return None

    @command.filters(filters.can_change_info)
    async def cmd_setgpic(self, ctx: command.Context) -> Optional[str]:
        """Set group picture"""
        msg = ctx.msg.reply_to_message or ctx.msg
        file = msg.photo or None

        if not file:
            return await self.text(ctx.chat.id, "gpic-no-photo")

        await self.bot.client.set_chat_photo(ctx.chat.id, photo=file.file_id)
        return await self.text(ctx.chat.id, "gpic-success-changed")

    async def cmd_adminlist(self, ctx: command.Context) -> str:
        """Get list of chat admins"""
        chat = ctx.chat
        if chat.type == ChatType.PRIVATE:
            return await self.text(chat.id, "err-chat-groups")
        admins = ""

        async for admin in util.tg.get_chat_admins(ctx.bot.client, chat.id):
            if admin.status == ChatMemberStatus.OWNER:
                admins += f"• {admin.user.mention} (**Creator**)\n"
            elif admin.user.id == self.bot.uid:
                admins += f"• {admin.user.mention} (**Me**)\n"
            elif admin.user.id == ctx.author.id:
                admins += f"• {admin.user.mention} (**You**)\n"
            else:
                admins += f"• {admin.user.mention}\n"

        return admins

    @command.filters(filters.can_restrict)
    async def cmd_zombies(self, ctx: command.Context) -> str:
        """Kick all deleted acc in group."""
        chat = ctx.chat
        zombie = 0

        await ctx.respond(await self.text(chat.id, "finding-zombie"))
        async for member in self.bot.client.get_chat_members(chat.id):  # type: ignore
            if member.user.is_deleted:
                zombie += 1
                try:
                    await self.bot.client.ban_chat_member(chat.id, member.user.id)
                except UserAdminInvalid:
                    zombie -= 1
                except FloodWait as flood:
                    await asyncio.sleep(flood.value)  # type: ignore

        if zombie == 0:
            return await self.text(chat.id, "zombie-clean")

        return await self.text(chat.id, "cleaning-zombie", zombie)

    @command.filters(filters.can_promote)
    async def cmd_promote(self, ctx: command.Context, user: Optional[User] = None) -> Optional[str]:
        """Bot promote member, required Both permission of can_promote"""
        chat = ctx.chat
        if not chat:
            return

        if not user:
            if ctx.input:
                return await self.text(chat.id, "err-peer-invalid")

            if not ctx.msg.reply_to_message or not ctx.msg.reply_to_message.from_user:
                return await self.text(chat.id, "no-promote-user")

            user = ctx.msg.reply_to_message.from_user

        if user.id == ctx.author.id:
            return await self.text(chat.id, "promote-error-self")

        if user.id == self.bot.uid:
            return await self.text(chat.id, "error-its-myself")

        bot, _ = await util.tg.fetch_permissions(self.bot.client, chat.id, user.id)
        if not bot:
            return await self.text(chat.id, "promote-error-perm")

        try:
            await chat.promote_member(user_id=user.id, privileges=bot.privileges)
        except ChatAdminRequired:
            return await self.text(chat.id, "promote-error-perm")
        except UserIdInvalid:
            return await self.text(chat.id, "promote-error-invalid")
        except UserPrivacyRestricted:
            return await self.text(chat.id, "promote-error-privacy-restricted")

        return await self.text(chat.id, "promote-success")

    @command.filters(filters.can_promote)
    async def cmd_demote(self, ctx: command.Context, user: Optional[User] = None) -> Optional[str]:
        """Demoter Just owner and promoter can demote admin."""
        chat = ctx.chat
        if not chat:
            return

        if not user:
            if ctx.input:
                return await self.text(chat.id, "err-peer-invalid")

            if not ctx.msg.reply_to_message or not ctx.msg.reply_to_message.from_user:
                return await self.text(chat.id, "no-demote-user")

            user = ctx.msg.reply_to_message.from_user

        if user.id == ctx.author.id:
            return await self.text(chat.id, "demote-error-self")

        if user.id == self.bot.uid:
            return await self.text(chat.id, "error-its-myself")

        try:
            await chat.promote_member(
                user_id=user.id,
                privileges=ChatPrivileges(
                    can_manage_chat=False,
                    can_delete_messages=False,
                    can_manage_video_chats=False,
                    can_restrict_members=False,
                    can_promote_members=False,
                    can_change_info=False,
                    can_post_messages=False,
                    can_edit_messages=False,
                    can_invite_users=False,
                    can_pin_messages=False,
                    is_anonymous=False,
                ),
            )
        except (BotChannelsNa, ChatAdminRequired):
            return await self.text(chat.id, "demote-error-perm")
        except UserCreator:
            return await self.text(chat.id, "demote-error-creator")

        return await self.text(chat.id, "demote-success")
