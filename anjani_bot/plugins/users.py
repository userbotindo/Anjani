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

from anjani_bot import anjani

__MODULE__ = "users"

USERS_DB = anjani.get_collection("USERS")
CHATS_DB = anjani.get_collection("CHATS")

class Users:

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
