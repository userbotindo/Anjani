""" Admin reporting plugin """
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

from pyrogram import filters
from pyrogram.errors import BadRequest

from anjani_bot import listener, plugin
from anjani_bot.utils import adminlist, user_ban_protected


class Reporting(plugin.Plugin):
    name = "Reporting"
    helpable = True

    async def __on_load__(self):
        self.report_db = self.bot.get_collection("CHAT_REPORTING")
        self.user_report_db = self.bot.get_collection("USER_REPORTING")
        self.lock = asyncio.Lock()

    async def __migrate__(self, old_chat_id, new_chat_id):
        async with self.lock:
            await self.report_db.update_one(
                {"chat_id": old_chat_id}, {"$set": {"chat_id": new_chat_id}}
            )

    async def __backup__(self, chat_id, data=None):
        if data and data.get(self.name):
            async with self.lock:
                await self.report_db.update_one(
                    {"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True
                )
        elif not data:
            return await self.report_db.find_one({"chat_id": chat_id}, {"_id": False})

    async def _change_setting(self, chat_id, is_private, setting) -> None:
        async with self.lock:
            if is_private:
                await self.user_report_db.update_one(
                    {"_id": chat_id}, {"$set": {"setting": setting}}, upsert=True
                )
            else:
                await self.report_db.update_one(
                    {"chat_id": chat_id}, {"$set": {"setting": setting}}, upsert=True
                )

    async def get_setting(self, identifier, is_private) -> bool:
        """Get current setting"""
        if is_private:
            data = await self.user_report_db.find_one({"_id": identifier})
        else:
            data = await self.report_db.find_one({"chat_id": identifier})
        if not data:
            return True
        return data.get("setting", True)

    @listener.on("report", filters.group)
    @listener.on(filters=filters.regex(r"^(?i)@admin(s)?\b") & filters.group, update="message")
    async def report(self, message):
        """Report a user"""
        chat_id = message.chat.id
        if not await self.get_setting(chat_id, False):
            return

        status = (await message.chat.get_member(message.from_user.id)).status
        if status in ["creator", "administrator"]:
            return  # ignore command from admins

        if not message.reply_to_message:
            return await message.reply_text(await self.bot.text(chat_id, "no-report-user"))
        reported_user = message.reply_to_message.from_user

        if message.reply_to_message.from_user.id == self.bot.identifier:
            return await message.reply_text(await self.bot.text(chat_id, "cant-report-me"))
        if message.reply_to_message.from_user.id == message.from_user.id:
            return await message.reply_text(await self.bot.text(chat_id, "cant-self-report"))
        if await user_ban_protected(self.bot, chat_id, reported_user.id):
            return await message.reply_text(await self.bot.text(chat_id, "cant-report-admin"))

        reported_mention = reported_user.mention
        reply_text = await self.bot.text(chat_id, "report-notif", reported_mention)
        admins = await adminlist(self.bot.client, chat_id)
        for admin in admins:
            if await self.get_setting(admin, True):
                reply_text += f"[\u200b](tg://user?id={admin})"
        await message.reply_text(reply_text)

    @listener.on("reports")
    async def report_setting(self, message):
        """Report setting command"""
        chat_id = message.chat.id
        if message.chat.type in ["group", "supergroup"]:
            user = await message.chat.get_member(message.from_user.id)
            if user.status not in ["creator", "administrator"]:
                return
            private = False
        elif message.chat.type == "private":
            private = True

        if message.command:
            args = message.command[0].lower()
            if args in ["on", "true", "yes"]:
                await self._change_setting(chat_id, private, True)
                key = "report-on" if private else "chat-report-on"
                await message.reply_text(await self.bot.text(chat_id, key))
            elif args in ["off", "false", "no"]:
                await self._change_setting(chat_id, private, False)
                key = "report-off" if private else "chat-report-off"
                await message.reply_text(await self.bot.text(chat_id, key))
            else:
                await message.reply(await self.bot.text(chat_id, "err-yes-no-args"))
        else:
            key = "report-setting" if private else "chat-report-setting"
            await message.reply_text(
                await self.bot.text(chat_id, key, await self.get_setting(chat_id, private))
            )
