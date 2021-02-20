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

from typing import ClassVar

from .. import command, plugin
from ..utils import adminlist


class Admin(plugin.Plugin):
    name: ClassVar[str] = "Admins"
    helpable: ClassVar[bool] = True

    @command.on_command("pin", can_pin=True)
    async def pin(self, message):
        """ Pin message on chats """
        if message.reply_to_message is None:
            return await message.reply(await self.text(message.chat.id, "error-reply-to-message"))
        is_silent = True
        if message.command and message.command[0] in [
                "notify",
                "loud",
                "violence",
        ]:
            is_silent = False
        await message.reply_to_message.pin(disable_notification=is_silent)

    @command.on_command("unpin", can_pin=True)
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

    @command.on_command("setgpic", can_change_info=True)
    async def change_g_pic(self, message):
        """ Set group picture """
        msg = message.reply_to_message or message
        file = msg.photo or None
        if file:
            await self.set_chat_photo(message.chat.id, photo=file.file_id)
        else:
            await message.reply_text(await self.text(message.chat.id, "gpic-no-photo"))

    @command.on_command("adminlist")
    async def admin_list(self, message):
        """ Get list of chat admins """
        adm_list = await adminlist(self, message.chat.id, full=True)
        admins = ""
        for i in adm_list:
            admins += f"- [{i['name']}](tg://user?id={i['id']})\n"
        await message.reply_text(admins)
