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

import codecs
from typing import ClassVar

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani_bot import anjani, plugin


class Staff(plugin.Plugin):
    name: ClassVar[str] = "Staff Tools"

    @anjani.on_command(["log", "logs"], staff_only=True)
    async def logs(self, message):
        """ Get bot logging as file """
        with codecs.open("anjani_bot/core/AnjaniBot.log", "r", encoding="utf-8") as log_file:
            data = log_file.read()
        async with self.http.post(
                "https://nekobin.com/api/documents",
                json={"content": data},
        ) as res:
            if res.status != 200:
                response = await res.json()
                key = response['result']['key']
                url = [
                    [
                        InlineKeyboardButton(text="View raw", url=f"https://nekobin.com/raw/{key}"),
                    ]
                ]
            else:
                return await message.reply_text("Failed to reach Nekobin")
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
