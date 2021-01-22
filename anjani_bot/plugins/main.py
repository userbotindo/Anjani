"""Main bot commands"""
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

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani_bot import anjani, plugin


class Main(plugin.Plugin):
    """ Bot main Commands """
    name: ClassVar[str] = "Main"

    @anjani.on_command("start")
    async def start(self, message):
        """ Bot start command """
        chat_id = message.chat.id

        if message.chat.type == "private":  # only send in PM's
            if message.command and message.command[0] == "help":
                return await message.reply_text(
                    await anjani.text(chat_id, "help-pm", anjani.name)
                )
            buttons = [
                [
                    InlineKeyboardButton(
                        text=await anjani.text(chat_id, "add-to-group-button"),
                        url=f"t.me/{anjani.username}?startgroup=true"
                    ),
                    InlineKeyboardButton(
                        text=await anjani.text(chat_id, "start-help-button"),
                        url=f"t.me/{anjani.username}?start=help",
                    ),
                ]
            ]
            return await message.reply_text(
                await anjani.text(chat_id, "start-pm", anjani.name),
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True,
                parse_mode="markdown",
            )
        return await message.reply_text(await anjani.text(chat_id, "start-chat"))

    @anjani.on_command("help")
    async def help(self, message):
        """ Bot modules helper """
        chat_id = message.chat.id

        if message.chat.type != "private":  # only send in PM's
            return await message.reply_text(
                await anjani.text(chat_id, "help-chat"),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=await anjani.text(chat_id, "help-chat-button"),
                                url=f"t.me/{anjani.username}?start=help"
                            )
                        ]
                    ]
                )
            )

        await message.reply_text(
            await anjani.text(chat_id, "help-pm", anjani.name)
        )

    @anjani.on_callback_query(filters.regex(r"help_(.*?)"))
    async def help_button(self, query):
        """ Bot helper button """
        # mod_match = re.match(r"help_module\((.+?)\)", query.data)
        # prev_match = re.match(r"help_prev\((.+?)\)", query.data)
        # next_match = re.match(r"help_next\((.+?)\)", query.data)
