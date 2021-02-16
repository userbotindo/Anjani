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

from .. import anjani, plugin

LOGGER = logging.getLogger(__name__)


class Language(plugin.Plugin):
    """ Bot language plugin """
    name: ClassVar[str] = "Language"

    async def __migrate__(self, old_chat, new_chat):
        await anjani.lang_col.update_one(
            {'chat_id': old_chat},
            {"$set": {'chat_id': new_chat}},
        )

    @staticmethod
    async def can_change_lang(client, message) -> bool:
        """ Check if user have rights to change chat language """
        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if not user.can_change_info:
            return False
        return True

    @staticmethod
    def parse_lang(lang_id: str) -> str:
        """ Return language name from language id. """
        if lang_id == 'en':
            return f"{emoji.FLAG_UNITED_STATES} English"
        if lang_id == 'id':
            return f"{emoji.FLAG_INDONESIA} Indonesia"
        LOGGER.error("Language code %s not defined", lang_id)
        return None

    @anjani.on_command(["lang", "setlang", "language"])
    async def set_lang(self, message):
        """ Set user/chat language. """
        chat_id = message.chat.id
        if message.chat.type != "private":  # Check admin rights
            if not (await Language.can_change_lang(self, message)):
                return await message.reply_text(
                    await self.text(chat_id, "error-no-rights")
                )
        chat_name = message.chat.first_name or message.chat.title
        lang = Language.parse_lang(await self.get_lang(chat_id))
        keyboard = []
        temp = []

        for count, i in enumerate(self.language, start=1):
            temp.append(
                InlineKeyboardButton(
                    Language.parse_lang(i), callback_data=f"set_lang_{i}"
                )
            )
            if count % 2 == 0:
                keyboard.append(temp)
                temp = []
            if count == len(self.language):
                keyboard.append(temp)

        await message.reply_text(
            await self.text(chat_id, "current-language", chat_name, lang),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    @anjani.on_callback_query(filters.regex(r"set_lang_(.*?)"))
    async def _lang_button(self, query):
        """ Set language query. """
        lang_match = re.findall(r"en|id", query.data)
        chat_id = query.message.chat.id

        if query.message.chat.type != "private":  # Check admin rights
            if not (await Language.can_change_lang(self, query.message)):
                return await query.answer(
                    await self.text(chat_id, "error-no-rights")
                )

        if lang_match:
            lang = Language.parse_lang(lang_match[0])
            if lang is None:
                return await query.edit_message_text(
                    await self.text(chat_id, "language-code-error")
                )
            await self.switch_lang(chat_id, lang_match[0])
            await query.edit_message_text(
                text=await self.text(chat_id, "language-set-succes", lang),
            )
