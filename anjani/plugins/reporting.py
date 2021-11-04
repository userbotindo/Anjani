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
from typing import Any, MutableMapping, Optional

from pyrogram.types import Message

from anjani import command, filters, listener, plugin, util


class Reporting(plugin.Plugin):
    name = "Reporting"
    helpable = True

    db: util.db.AsyncCollection
    user_db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("CHAT_REPORTING")
        self.user_db = self.bot.db.get_collection("USER_REPORTING")

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        report = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        return {self.name: report} if report else {}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True)

    @listener.filters(filters.regex(r"^(?i)@admin(s)?\b") & filters.group)
    async def on_message(self, message: Message) -> None:
        chat = message.chat
        if not await self.is_active(chat.id, is_private=False):
            return

        invoker = await chat.get_member(message.from_user.id)
        if invoker.status in {"creator", "administrator"}:
            return  # ignore command from admins

        if not message.reply_to_message:
            await message.reply(await self.text(chat.id, "no-report-user"))
            return

        reported_user = message.reply_to_message.from_user

        if reported_user.id == self.bot.uid:
            await message.reply_text(await self.text(chat.id, "cant-report-me"))
            return
        if reported_user.id == message.from_user.id:
            await message.reply_text(await self.text(chat.id, "cant-self-report"))
            return

        member = await chat.get_member(reported_user.id)
        if util.tg.is_staff_or_admin(member):
            await message.reply_text(await self.text(chat.id, "cant-report-admin"))
            return

        reply_text = await self.text(chat.id, "report-notif", util.tg.mention(reported_user))
        slots = 4096 - len(reply_text)
        async for admin in util.tg.get_chat_admins(self.bot.client, chat.id, exclude_bot=True):
            if await self.is_active(admin.user.id, True):
                reply_text += f"[\u200b](tg://user?id={admin.user.id})"

            slots -= 1
            if slots == 0:
                break

        await message.reply_text(reply_text)

    async def setting(self, chat_id: int, is_private: bool, setting: bool) -> None:
        if is_private:
            await self.user_db.update_one(
                {"_id": chat_id}, {"$set": {"setting": setting}}, upsert=True
            )
        else:
            await self.db.update_one(
                {"chat_id": chat_id}, {"$set": {"setting": setting}}, upsert=True
            )

    async def is_active(self, uid: int, is_private: bool) -> bool:
        """Get current setting default to True"""
        if is_private:
            data = await self.user_db.find_one({"_id": uid})
        else:
            data = await self.db.find_one({"chat_id": uid})
        if not data:
            return True

        return data.get("setting", True)

    async def cmd_report(self, ctx: command.Context) -> None:
        return await self.on_message(ctx.message)

    @command.filters(filters.admin_only)
    async def cmd_reports(
        self, ctx: command.Context, setting: Optional[bool] = None
    ) -> Optional[str]:
        """Report setting command"""
        if ctx.msg.reply_to_message:
            return None

        chat = ctx.chat
        private = chat.type == "private"

        if setting is None:
            if not ctx.input:
                return await self.text(
                    chat.id,
                    "report-setting" if private else "chat-report-setting",
                    await self.is_active(chat.id, private),
                )

            return await self.text(chat.id, "err-yes-no-args")

        _, member = await util.tg.fetch_permissions(self.bot.client, chat.id, ctx.author.id)
        if member.status not in {"administrator", "creator"}:
            return None

        if setting is True:
            text = "report-on" if private else "chat-report-on"
        else:
            text = "report-off" if private else "chat-report-off"

        ret, _ = await asyncio.gather(
            self.text(chat.id, text),
            self.setting(chat.id, private, setting),
        )
        return ret
