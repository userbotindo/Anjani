"""User language setting"""
# Copyright (C) 2020 - 2023  UserbotIndo Team, <https://github.com/userbotindo.git>
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
from typing import Any, ClassVar, MutableMapping, Optional

from pyrogram import emoji
from pyrogram.enums.chat_type import ChatType
from pyrogram.errors import MessageNotModified
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from anjani import command, filters, listener, plugin, util

LANG_FLAG = {
    "en": f"{emoji.FLAG_UNITED_STATES} English",
    "id": f"{emoji.FLAG_INDONESIA} Indonesia",
}


class Language(plugin.Plugin):
    """Bot language plugin"""

    name: ClassVar[str] = "Language"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("LANGUAGE")

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        language = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        return {self.name: language} if language else {}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True)

    @listener.filters(filters.regex(r"set_lang_(.*)"))
    async def on_callback_query(self, query: CallbackQuery) -> None:
        """Set language query."""
        lang_match = query.matches[0].group(1)
        chat = query.message.chat

        # Check admin rights
        if chat.type != ChatType.PRIVATE:
            user = await chat.get_member(query.from_user.id)
            if not user.privileges or not user.privileges.can_change_info:
                await query.answer(await self.text(chat.id, "error-no-rights"))
                return

        lang = LANG_FLAG.get(lang_match)
        if not lang:
            await query.edit_message_text(await self.text(chat.id, "language-code-error"))
            return

        await self.switch_lang(chat.id, lang_match)
        try:
            await query.answer()
            await query.edit_message_text(
                text=await self.text(chat.id, "language-set-succes", lang),
            )
        except MessageNotModified:
            await query.answer(
                await self.text(chat.id, "language-set-succes", lang), show_alert=True
            )
            await query.message.delete()

    async def switch_lang(self, chat_id: int, language: str) -> None:
        """Change chat language setting."""
        if language == "en":
            await self.db.delete_one({"chat_id": int(chat_id)})
        else:
            await self.db.update_one(
                {"chat_id": int(chat_id)},
                {"$set": {"language": language}},
                upsert=True,
            )
        self.bot.chats_languages[chat_id] = language

    @command.filters(aliases=["lang", "language"])
    async def cmd_setlang(self, ctx: command.Context) -> Optional[str]:
        """Set user/chat language."""
        chat = ctx.chat

        # Check admin rights
        if chat.type != ChatType.PRIVATE:
            user = await chat.get_member(ctx.msg.from_user.id)
            if not user.privileges or not user.privileges.can_change_info:
                return await self.text(chat.id, "error-no-rights")

        if ctx.input:
            lang = ctx.input.lower()
            if lang in self.bot.languages:
                await asyncio.gather(
                    self.switch_lang(chat.id, lang),
                    ctx.respond(await self.text(chat.id, "language-set-succes", LANG_FLAG[lang])),
                )
            else:
                return await self.text(chat.id, "language-invalid", list(self.bot.languages.keys()))
        else:
            chat_name = chat.first_name or chat.title
            lang = LANG_FLAG[self.bot.chats_languages.get(chat.id, "en")]
            keyboard = []
            temp = []

            for count, i in enumerate(self.bot.languages.keys(), start=1):
                temp.append(InlineKeyboardButton(LANG_FLAG[i], callback_data=f"set_lang_{i}"))
                if count % 2 == 0:
                    keyboard.append(temp)
                    temp = []
                if count == len(self.bot.languages):
                    keyboard.append(temp)
            await ctx.respond(
                await self.text(chat.id, "current-language", chat_name, lang),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        return None
