"""staff's commands"""
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
import codecs
import logging
from io import BytesIO
from typing import ClassVar

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid,
    PeerIdInvalid,
    UserNotParticipant
)

from anjani_bot import anjani, plugin
from anjani_bot.utils import nekobin
from anjani_bot.plugins import users

LOGGER = logging.getLogger(__name__)

class Staff(plugin.Plugin):
    name: ClassVar[str] = "Staff Tools"

    @anjani.on_command(["log", "logs"], staff_only=True)
    async def logs(self, message):
        """ Get bot logging as file """
        with codecs.open("anjani_bot/core/AnjaniBot.log", "r", encoding="utf-8") as log_file:
            data = log_file.read()
        key = await nekobin(self, data)
        if key:
            url = [[
                InlineKeyboardButton(text="View raw", url=f"https://nekobin.com/raw/{key}"),
            ]]
            await self.send_document(
                message.from_user.id,
                "anjani_bot/core/AnjaniBot.log",
                caption="Bot logs",
                file_name="AnjaniBot.log",
                force_document=True,
                reply_markup=InlineKeyboardMarkup(url),
            )
            if message.chat.type != "private":
                await message.reply_text("I've send the log on PM's :)")
        else:
            await message.reply_text("Failed to reach Nekobin")

    @anjani.on_command("broadcast", staff_only=True)
    async def broadcast(self, message):
        """ Broadcast a message to all chats """
        to_send = message.text.split(None, 1)
        if len(to_send) >= 2:
            failed = 0
            sent = 0
            text = to_send[1] + "\n\nThis is broadcast message."
            msg = await message.reply_text("sending broadcast...")
            async for chat in users.Users.chats_db(self).find({}):
                if sent % 25 == 0:
                    # sleep every 25 msg sent to prevent flood limmit.
                    await asyncio.sleep(1)
                try:
                    await anjani.send_message(chat["chat_id"], text)
                    sent += 1
                except (PeerIdInvalid, ChannelInvalid):
                    failed += 1
                    LOGGER.warning(
                        "Can't send broadcast to \"%s\" with id %s",
                        chat["chat_name"],
                        chat["chat_id"]
                    )
            await msg.edit_text(
                "Broadcast complete!\n"
                f"{sent} groups succeed, {failed} groups failed to receive the message"
            )

    @anjani.on_command(["leave", "leavechat", "leavegroup"], staff_only=True)
    async def leavechat(self, message):
        """ leave the given chat_id """
        try:
            await anjani.leave_chat(message.command[0])
            await message.reply_text("Left the group successfully!")
        except (PeerIdInvalid, UserNotParticipant):
            await message.reply_text("I'm not a member on that group")
        except IndexError:
            await message.reply_text("Give me the chat id!")


    @anjani.on_command("chatlist", staff_only=True)
    async def chatlist(self, message):
        """ Send file of chat's I'm in """
        chatfile = "List of chats.\n"
        async for chat in users.Users.chats_db(self).find({}):
            chatfile += "{} - ({})\n".format(chat["chat_name"], chat["chat_id"])

        with BytesIO(str.encode(chatfile)) as output:
            output.name = "chatlist.txt"
            await message.reply_document(
                document=output,
                caption="Here is the list of chats in my database.",
            )
