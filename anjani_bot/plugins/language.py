"""User language setting"""
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

import logging
import re
from typing import ClassVar

from pyrogram import emoji, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani_bot import listener, plugin

LOGGER = logging.getLogger(__name__)


class Language(plugin.Plugin):
    """ Bot language plugin """
    name: ClassVar[str] = "Language"
    helpable: ClassVar[bool] = True

    async def __migrate__(self, old_chat, new_chat):
        await self.bot.lang_col.update_one(
            {'chat_id': old_chat},
            {"$set": {'chat_id': new_chat}},
        )

    async def can_change_lang(self, chat_id, user_id) -> bool:
        """ Check if user have rights to change chat language """
        user = await self.bot.client.get_chat_member(chat_id, user_id)
        return not user.can_change_info

    @staticmethod
    def parse_lang(lang_id: str) -> str:
        """ Return language name from language id. """
        if lang_id == 'en':
            return f"{emoji.FLAG_UNITED_STATES} English"
        if lang_id == 'id':
            return f"{emoji.FLAG_INDONESIA} Indonesia"
        LOGGER.error("Language code %s not defined", lang_id)
        return None

    @listener.on(["lang", "setlang", "language"])
    async def set_lang(self, message):
        """ Set user/chat language. """
        chat_id = message.chat.id
        if message.chat.type != "private":  # Check admin rights
            if await self.can_change_lang(chat_id, message.from_user.id):
                return await message.reply_text(
                    await self.bot.text(chat_id, "error-no-rights")
                )

        if len(message.command) >= 1:
            change = message.command[0]
            if change in self.bot.language:
                await self.bot.switch_lang(chat_id, change)
                lang = self.parse_lang(change)
                await message.reply_text(
                    text=await self.bot.text(chat_id, "language-set-succes", lang),
                )
            else:
                await message.reply_text(
                    await self.bot.text(chat_id, "language-invalid", self.language)
                )
        else:
            chat_name = message.chat.first_name or message.chat.title
            lang = self.parse_lang(await self.bot.get_lang(chat_id))
            keyboard = []
            temp = []

            for count, i in enumerate(self.bot.language, start=1):
                temp.append(
                    InlineKeyboardButton(
                        self.parse_lang(i), callback_data=f"set_lang_{i}"
                    )
                )
                if count % 2 == 0:
                    keyboard.append(temp)
                    temp = []
                if count == len(self.bot.language):
                    keyboard.append(temp)

            keyboard += [[InlineKeyboardButton(
                "Help us translating language", url="https://crowdin.com/project/anjani-bot"
            )]]

            await message.reply_text(
                await self.bot.text(chat_id, "current-language", chat_name, lang),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    @listener.on(filters=filters.regex(r"set_lang_(.*?)"), update="callbackquery")
    async def _lang_button(self, query):
        """ Set language query. """
        lang_match = re.findall(r"en|id", query.data)
        chat_id = query.message.chat.id

        if query.message.chat.type != "private":  # Check admin rights
            if await self.can_change_lang(chat_id, query.from_user.id):
                return await query.answer(
                    await self.bot.text(chat_id, "error-no-rights")
                )

        if lang_match:
            lang = self.parse_lang(lang_match[0])
            if lang is None:
                return await query.edit_message_text(
                    await self.bot.text(chat_id, "language-code-error")
                )
            await self.bot.switch_lang(chat_id, lang_match[0])
            await query.edit_message_text(
                text=await self.bot.text(chat_id, "language-set-succes", lang),
            )
