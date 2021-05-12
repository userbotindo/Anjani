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

import re
from typing import ClassVar

from pyrogram import filters
from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani_bot import listener, plugin


class Main(plugin.Plugin):
    """Bot main Commands"""

    name: ClassVar[str] = "Main"

    @listener.on("start")
    async def start(self, message):
        """Bot start command"""
        chat_id = message.chat.id

        if message.chat.type == "private":  # only send in PM's
            if message.command and message.command[0] == "help":
                keyboard = await self.bot.help_builder(chat_id)
                return await message.reply_text(
                    await self.bot.text(chat_id, "help-pm", self.bot.name),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            buttons = [
                [
                    InlineKeyboardButton(
                        text=await self.bot.text(chat_id, "add-to-group-button"),
                        url=f"t.me/{self.bot.username}?startgroup=true",
                    ),
                    InlineKeyboardButton(
                        text=await self.bot.text(chat_id, "start-help-button"),
                        url=f"t.me/{self.bot.username}?start=help",
                    ),
                ]
            ]
            return await message.reply_text(
                await self.bot.text(chat_id, "start-pm", self.bot.name),
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True,
                parse_mode="markdown",
            )
        return await message.reply_text(await self.bot.text(chat_id, "start-chat"))

    @listener.on("help")
    async def help(self, message):
        """Bot plugins helper"""
        chat_id = message.chat.id

        if message.chat.type != "private":  # only send in PM's
            return await message.reply_text(
                await self.bot.text(chat_id, "help-chat"),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=await self.bot.text(chat_id, "help-chat-button"),
                                url=f"t.me/{self.bot.username}?start=help",
                            )
                        ]
                    ]
                ),
            )
        keyboard = await self.bot.help_builder(chat_id)
        await message.reply_text(
            await self.bot.text(chat_id, "help-pm", self.bot.name),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    @listener.on(filters=filters.regex(r"help_(.*?)"), update="callbackquery")
    async def help_button(self, query):
        """Bot helper button"""
        plugin_match = re.match(r"help_plugin\((.+?)\)", query.data)
        back_match = re.match(r"help_back", query.data)
        chat_id = query.message.chat.id

        if plugin_match:
            extension = plugin_match.group(1)
            text = "Here is the help for the **{}** plugin:\n\n{}".format(
                extension.capitalize(),
                await self.bot.text(chat_id, f"{extension}-help"),
            )
            try:
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    await self.bot.text(chat_id, "back-button"),
                                    callback_data="help_back",
                                )
                            ]
                        ]
                    ),
                    parse_mode="markdown",
                )
            except MessageNotModified:
                pass
        elif back_match:
            keyboard = await self.bot.help_builder(chat_id)
            try:
                await query.edit_message_text(
                    await self.bot.text(chat_id, "help-pm", self.bot.name),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="markdown",
                )
            except MessageNotModified:
                pass

    @listener.on("markdownhelp")
    async def markdown_helper(self, message):
        """Send markdown helper."""
        await message.reply_text(
            await self.bot.text(message.chat.id, "markdown-helper", self.bot.name),
            parse_mode="html",
            disable_web_page_preview=True,
        )
