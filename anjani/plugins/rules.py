"""Bot rules command"""
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

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani_bot import listener, plugin


class Rules(plugin.Plugin):
    name = "Rules"
    helpable = True

    async def __on_load__(self):
        self.rules_db = self.bot.get_collection("RULES")

    async def __migrate__(self, old_chat, new_chat):
        await self.rules_db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def __backup__(self, chat_id, data=None):
        if data and data.get(self.name):
            await self.rules_db.update_one(
                {"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True
            )
        elif not data:
            return await self.rules_db.find_one({"chat_id": chat_id}, {"_id": False})

    @listener.on("setrules", admin_only=True)
    async def set_rules(self, message):
        chat_id = message.chat.id
        if not message.command:
            return await message.reply_text(await self.bot.text(chat_id, "rules-blank-err"))

        content = message.text.markdown.split(None, 1)
        await self.rules_db.update_one(
            {"chat_id": chat_id}, {"$set": {"rules": content[1]}}, upsert=True
        )
        return await message.reply_text(
            await self.bot.text(
                chat_id, "rules-set", f"t.me/{self.bot.username}?start=rules_{chat_id}"
            )
        )

    @listener.on("clearrules", admin_only=True)
    async def clear_rules(self, message):
        chat_id = message.chat.id
        await self.rules_db.delete_one({"chat_id": chat_id})
        await message.reply_text(await self.bot.text(chat_id, "rules-clear"))

    @listener.on("rules")
    async def rules(self, message):
        chat_id = message.chat.id
        content = await self.rules_db.find_one({"chat_id": chat_id})
        if not content:
            return await message.reply_text(await self.bot.text(chat_id, "rules-none"))
        await message.reply_text(
            await self.bot.text(chat_id, "rules-view-caption"),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=await self.bot.text(chat_id, "rules-button"),
                            url=f"t.me/{self.bot.username}?start=rules_{chat_id}",
                        )
                    ]
                ]
            ),
        )
