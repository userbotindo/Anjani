"""Admin Plugin, Can manage your Group. """
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
from typing import ClassVar

from pyrogram.errors import UserAdminInvalid, FloodWait

from anjani_bot import listener, plugin, extract_user_and_text
from anjani_bot.utils import adminlist


class Admin(plugin.Plugin):
    name: ClassVar[str] = "Admins"
    helpable: ClassVar[bool] = True

    @listener.on("pin", can_pin=True)
    async def pin(self, message):
        """ Pin message on chats """
        if message.reply_to_message is None:
            return await message.reply(
                await self.bot.text(message.chat.id, "error-reply-to-message")
            )
        is_silent = True
        if message.command and message.command[0] in [
            "notify",
            "loud",
            "violence",
        ]:
            is_silent = False
        await message.reply_to_message.pin(disable_notification=is_silent)

    @listener.on("unpin", can_pin=True)
    async def unpin(self, message):
        """ Unpin message on chats """
        chat_id = message.chat.id
        chat = await self.bot.client.get_chat(chat_id)
        if message.command and message.command[0] == "all":
            await self.bot.client.unpin_all_chat_messages(chat_id)
        elif message.reply_to_message is None:
            pinned = chat.pinned_message.message_id
            await self.bot.client.unpin_chat_message(chat_id, pinned)
        else:
            await message.reply_to_message.unpin()

    @listener.on("setgpic", can_change_info=True)
    async def change_g_pic(self, message):
        """ Set group picture """
        msg = message.reply_to_message or message
        file = msg.photo or None
        if file:
            await self.bot.client.set_chat_photo(message.chat.id, photo=file.file_id)
        else:
            await message.reply_text(await self.bot.text(message.chat.id, "gpic-no-photo"))

    @listener.on("adminlist")
    async def admin_list(self, message):
        """ Get list of chat admins """
        if message.chat.type == "private":
            return await message.reply_text(
                await self.bot.text(message.chat.id, "error-chat-private")
            )
        adm_list = await adminlist(self.bot.client, message.chat.id, full=True)
        admins = ""
        for i in adm_list:
            admins += f"- [{i['name']}](tg://user?id={i['id']})\n"
        await message.reply_text(admins)

    @listener.on("zombies", can_restrict=True)
    async def zombie_clean(self, message):
        """ Kick all deleted acc in group. """
        chat_id = message.chat.id
        zombie = 0

        msg = await message.reply(await self.bot.text(chat_id, "finding-zombie"))
        async for member in self.bot.client.iter_chat_members(chat_id):
            if member.user.is_deleted:
                zombie += 1
                try:
                    await self.bot.client.kick_chat_member(chat_id, member.user.id)
                except UserAdminInvalid:
                    zombie -= 1
                except FloodWait as flood:
                    await asyncio.sleep(flood.x)

        if zombie == 0:
            return await msg.edit(await self.bot.text(chat_id, "zombie-clean"))
        await msg.edit_text(await self.bot.text(chat_id, "cleaning-zombie", zombie))

    @listener.on("promote", can_promote=True)
    async def promoter(self, message):
        """ Bot promote member, required Both permission of can_promote"""
        chat_id = message.chat.id
        user, _ = extract_user_and_text(message)

        if user is None:
            return await message.reply(await self.bot.text(chat_id, "no-promote-user"))

        # bot can't assign higher perms than itself!
        bot_perm = await self.bot.client.get_chat_member(chat_id, "me")
        await self.bot.client.promote_chat_member(
            chat_id=chat_id,
            user_id=user,
            can_change_info=bot_perm.can_change_info,
            can_post_messages=bot_perm.can_post_messages,
            can_edit_messages=bot_perm.can_edit_messages,
            can_be_edited=bot_perm.can_be_edited,
            can_delete_messages=bot_perm.can_delete_messages,
            can_restrict_members=bot_perm.can_restrict_members,
            can_promote_members=bot_perm.can_promote_members,
            can_invite_users=bot_perm.can_invite_users,
            can_pin_messages=bot_perm.can_pin_messages,
        )
        await message.reply_text(await self.bot.text(chat_id, "promote-succes"))

    @listener.on("demote", can_promote=True)
    async def demoter(self, message):
        """ Demoter Just owner and promoter can demote admin."""
        chat_id = message.chat.id
        user, _ = extract_user_and_text
        prmtby = (await self.bot.client.get_chat_member(chat_id, user)).promoted_by.id
        dmtr = await self.bot.client.get_chat_memeber(chat_id, message.from_user.id)

        if user is None:
            return await message.reply(await self.bot.text(chat_id, "no-demote-user"))
        # Demoter must be owners or promoter
        if dmtr != prmtby and dmtr.status != "creator":
            return await message.reply(await self.bot.text(chat_id, "not-promoter"))

        await self.bot.client.promote_chat_member(
            chat_id=chat_id,
            user_id=user,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_be_edited=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_invite_users=False,
            can_pin_messages=False,
        )
        await message.reply(await self.bot.text(chat_id, "demote-succes"))
