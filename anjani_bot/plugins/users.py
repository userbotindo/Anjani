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

from pyrogram import filters
from typing import ClassVar

from anjani_bot import anjani
from .. import plugin


USERS_DB = anjani.get_collection("USERS")
CHATS_DB = anjani.get_collection("CHATS")


class Users(plugin.Plugin):
    name: ClassVar[str] = "Users"

    @anjani.on_message(filters.all & filters.group, group=4)
    async def log_user(self, message):
        """ User database. """
        chat = message.chat
        user = message.from_user

        await USERS_DB.update_one(
            {'_id': user.id},
            {
                "$set": {'username': user.username},
                "$addToSet": {'chats': chat.id}
            },
            upsert=True,
        )

        if not (chat.id or chat.title):
            return

        await CHATS_DB.update_one(
            {'chat_id': chat.id},
            {
                "$set": {'chat_name': chat.title},
                "$addToSet": {'member': user.id}
            },
            upsert=True,
        )

    @anjani.on_message(filters.left_chat_member, group=7)
    async def del_log_user(self, message):
        """ Delete user data from chats """
        chat_id = message.chat.id
        user_id = message.left_chat_member.id

        await USERS_DB.update_one(
            {'_id': user_id},
            {"$pull" : {'chats': chat_id}}
        )

        await CHATS_DB.update_one(
            {'chat_id': chat_id},
            {"$pull": {'member': user_id}}
        )
