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

from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant

from anjani_bot import anjani, plugin
from anjani_bot.utils import extract_user_and_text, user_ban_protected, adminlist


class Admin(plugin.Plugin):
    name: ClassVar[str] = "Admins"

    @anjani.on_command("pin", can_pin=True)
    async def pin(self, message):
        """ Pin message on chats """
        if message.reply_to_message is None:
            return await message.reply(
                await self.text(message.chat.id, "error-reply-to-message")
            )
        is_silent = True
        if message.command and message.command[0] in ["notify", "loud", "violence"]:
            is_silent = False
        await message.reply_to_message.pin(disable_notification=is_silent)

    @anjani.on_command("unpin", can_pin=True)
    async def unpin(self, message):
        """ Unpin message on chats """
        chat_id = message.chat.id
        chat = await self.get_chat(chat_id)
        if message.command and message.command[0] == "all":
            await self.unpin_all_chat_messages(chat_id)
        elif message.reply_to_message is None:
            pinned = chat.pinned_message.message_id
            await self.unpin_chat_message(chat_id, pinned)
        else:
            await message.reply_to_message.unpin()

    @anjani.on_command("del", can_delete=True)
    async def del_message(self, message):
        """ Delete replied message """
        if message.reply_to_message:
            await message.reply_to_message.delete()
            await message.delete()
        else:
            await message.reply_text(
                await self.text(message.chat.id, "error-reply-to-message")
            )

    @anjani.on_command(["purge", "prune"], can_delete=True)
    async def purge_message(self, message):
        """ purge message from message replied """
        if message.reply_to_message:
            purged = 0
            msg = await message.reply_text(
                await self.lang(message.chat.id, "purge")
                )
            for msg_id in reversed(range(
                    message.reply_to_message.message_id,
                    message.message_id
            )):
                await self.delete_messages(
                    message.chat.id,
                    msg_id
                )
                purged += 1
            await message.delete()
            await msg.edit(
                await self.text(message.chat.id, "purge-done", purged)
            )
            await asyncio.sleep(5)
            await msg.delete()
        else:
            await message.reply_text(
                await self.text(message.chat.id, "error-reply-to-message")
            )

    @anjani.on_command("kick", can_restrict=True)
    async def kick_member(self, message):
        """ Kick chat member """
        user, _ = extract_user_and_text(message)
        chat_id = message.chat.id
        if user is None:
            return await message.reply_text(await self.lang(chat_id, "no-kick-user"))
        try:
            if await user_ban_protected(self, chat_id, user):
                return await message.reply_text(await self.lang(chat_id, "admin-kick"))
        except UserNotParticipant:
            return await message.reply_text(
                await self.text(chat_id, "err-not-participant")
            )
        await message.chat.kick_member(user)
        await message.chat.unban_member(user)
        await message.reply_text(await self.text(chat_id, "kick-done"))

    @anjani.on_command("ban", can_restrict=True)
    async def ban_member(self, message):
        """ Ban chat member """
        user, _ = extract_user_and_text(message)
        chat_id = message.chat.id
        if user is None:
            return await message.reply_text("Who should i ban?\nis it you?")
        try:
            if await user_ban_protected(self, chat_id, user):
                return await message.reply_text(
                    await self.text(chat_id, "no-ban-user")
                )
        except UserNotParticipant:
            return await message.reply_text(
                await self.text(chat_id, "err-not-participant")
            )
        await message.chat.kick_member(user)
        await message.reply_text(await self.text(chat_id, "ban-done"))

    @anjani.on_command("unban", can_restrict=True)
    async def unban_member(self, message):
        """ Unban chat member """
        user, _, = extract_user_and_text(message)
        if user is None:
            return await message.reply_text(
                await self.text(message.chat.id, "unban-no-user")
            )
        await message.chat.unban_member(user)
        await message.reply_text(await self.text(message.chat.id, "unban-done"))

    @anjani.on_command("setgpic", can_change_info=True)
    async def change_g_pic(self, message):
        """ Set group picture """
        msg = message.reply_to_message or message
        file = msg.photo or None
        if file:
            await self.set_chat_photo(message.chat.id, photo=file.file_id)
        else:
            await message.reply_text(await self.text(message.chat.id, "gpic-no-photo"))

    @anjani.on_command("adminlist")
    async def admin_list(self, message):
        """ Get list of chat admins """
        adm_list = await adminlist(self, message.chat.id, full=True)
        admins = ""
        for i in adm_list:
            admins += f"- [{i['name']}](tg://user?id={i['id']})\n"
        await message.reply_text(admins)
