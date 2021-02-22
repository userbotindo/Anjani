"""User data management"""
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
from typing import ClassVar

from motor.motor_asyncio import AsyncIOMotorCollection
from pyrogram import filters

from anjani_bot import listener, plugin


class Users(plugin.Plugin):
    name: ClassVar[str] = "Users"

    db_chats: AsyncIOMotorCollection
    db_users: AsyncIOMotorCollection
    lock = asyncio.locks.Lock

    async def __on_load__(self) -> None:
        self.chats_db = self.bot.get_collection("CHATS")
        self.users_db = self.bot.get_collection("USERS")
        self.lock = asyncio.Lock()

    async def __migrate__(self, old_chat, new_chat) -> None:
        async with self.lock:
            await self.users_db.update_many(
                {'chats': old_chat},
                {"$push": {'chats': new_chat}},
            )
            await self.users_db.update_many(
                {'chats': old_chat},
                {"$pull": {'chats': old_chat}},
            )

            await self.chats_db.update_one(
                {'chat_id': old_chat},
                {"$set": {'chat_id': new_chat}}
            )

    @listener.on(filters=filters.all & filters.group, group=4, update="message")
    async def log_user(self, message):
        """ User database. """
        chat = message.chat
        user = message.from_user

        if not user:  # sanity check for service message
            return

        async with self.lock:
            await self.users_db.update_one(
                {'_id': user.id},
                {
                    "$set": {'username': user.username},
                    "$addToSet": {'chats': chat.id}
                },
                upsert=True,
            )

            if not (chat.id or chat.title):
                return

            await self.chats_db.update_one(
                {'chat_id': chat.id},
                {
                    "$set": {'chat_name': chat.title},
                    "$addToSet": {'member': user.id}
                },
                upsert=True,
            )

    @listener.on(filters=filters.left_chat_member, group=7, update="message")
    async def del_log_user(self, message):
        """ Delete user data from chats """
        chat_id = message.chat.id
        user_id = message.left_chat_member.id
        async with self.lock:
            if user_id == self.bot.identifier:
                await self.chats_db.delete_one(
                    {'chat_id': chat_id}
                )
                await self.users_db.update_many(
                    {'chats': chat_id},
                    {"$pull": {'chats': chat_id}},
                )
            else:
                await self.users_db.update_one(
                    {'_id': user_id},
                    {"$pull": {'chats': chat_id}}
                )

                await self.chats_db.update_one(
                    {'chat_id': chat_id},
                    {"$pull": {'member': user_id}}
                )

    @listener.on(filters=filters.migrate_from_chat_id, update="message")
    async def __chat_migrate(self, message):
        """ Chat migrate handler """
        old_chat = message.migrate_from_chat_id
        new_chat = message.chat.id
        await self.bot.migrate_chat(old_chat, new_chat)
