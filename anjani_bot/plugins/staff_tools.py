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
import os
from datetime import datetime
from io import BytesIO
from typing import ClassVar, List

from motor.motor_asyncio import AsyncIOMotorCollection
from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid,
    PeerIdInvalid,
    UserNotParticipant,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani_bot import listener, plugin
from anjani_bot.utils import dogbin

LOGGER = logging.getLogger(__name__)


class Staff(plugin.Plugin):
    name: ClassVar[str] = "Staff Tools"

    db: AsyncIOMotorCollection

    async def __on_load__(self) -> None:
        self.db = self.bot.get_collection("CHATS")

    @listener.on(["log", "logs"], staff_only=True)
    async def logs(self, message):
        """Get bot logging as file"""
        core_path = "anjani_bot/core"
        if message.command:
            log_file = os.path.join(core_path, message.command[0])
        else:
            log_file = os.path.join(
                core_path, f"AnjaniBot-{datetime.now().strftime('%Y-%m-%d')}.log"
            )
        if not os.path.exists(log_file):
            files: List[str] = []
            for file in os.listdir(core_path):
                if file.endswith(".log"):
                    files.append(file)

            if len(files) == 1:
                log_file = os.path.join(core_path, files[0])
            else:
                text = "Here's the list available file:\n"
                for log_file in files:
                    text += f"  **-** `{log_file}`\n"
                await message.reply_text(text)
                return

        with codecs.open(log_file, "r", encoding="utf-8") as log_buffer:
            data = log_buffer.read()
        key = await dogbin(self.bot, data)
        text = "**Bot Log**"
        if key:
            button = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="View raw", url=f"https://del.dog/raw/{key}"),
                    ]
                ]
            )
        else:
            button = None
            text += "\n*Falied to reach Dogbin, only sending file"

        if message.chat.type != "private":
            await message.reply_text("I've send the log on PM's :)")
        await self.bot.client.send_document(
            message.from_user.id,
            log_file,
            caption=text,
            file_name=f"{log_file.split('/')[-1]}",
            force_document=True,
            reply_markup=button,
        )

    @listener.on("broadcast", staff_only="owner")
    async def broadcast(self, message):
        """Broadcast a message to all chats"""
        to_send = message.text.split(None, 1)
        if len(to_send) >= 2:
            failed = 0
            sent = 0
            text = to_send[1] + "\n\n*This is a broadcast message."
            msg = await message.reply_text("sending broadcast...")
            async for chat in self.db.find({}):
                if sent % 25 == 0:
                    # sleep every 25 msg sent to prevent flood limmit.
                    await asyncio.sleep(1)
                try:
                    await self.bot.client.send_message(chat["chat_id"], text)
                    sent += 1
                except (PeerIdInvalid, ChannelInvalid):
                    failed += 1
                    LOGGER.warning(
                        f"Can't send broadcast to \"{chat['chat_name']}\" "
                        f"with id {chat['chat_id']}",
                    )
            await msg.edit_text(
                "Broadcast complete!\n"
                f"{sent} groups succeed, {failed} groups failed to receive the message"
            )

    @listener.on(["leave", "leavechat", "leavegroup"], staff_only=True)
    async def leavechat(self, message):
        """leave the given chat_id"""
        try:
            await self.bot.client.leave_chat(message.command[0])
            await message.reply_text("Left the group successfully!")
        except (PeerIdInvalid, UserNotParticipant):
            await message.reply_text("I'm not a member on that group")
        except IndexError:
            await message.reply_text("Give me the chat id!")

    @listener.on("chatlist", staff_only=True)
    async def chatlist(self, message):
        """Send file of chat's I'm in"""
        chatfile = "List of chats.\n"
        async for chat in self.db.find({}):
            chatfile += "{} - ({})\n".format(chat["chat_name"], chat["chat_id"])

        with BytesIO(str.encode(chatfile)) as output:
            output.name = "chatlist.txt"
            await message.reply_document(
                document=output,
                caption="Here is the list of chats in my database.",
            )
