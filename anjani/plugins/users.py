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
from typing import ClassVar, Optional

from aiopath import AsyncPath
from pyrogram.types import Message, User

from anjani import command, plugin, util


class Users(plugin.Plugin):
    name: ClassVar[str] = "Users"

    chats_db: util.db.AsyncCollection
    users_db: util.db.AsyncCollection
    lock: asyncio.locks.Lock

    async def on_load(self) -> None:
        self.chats_db = self.bot.db.get_collection("CHATS")
        self.users_db = self.bot.db.get_collection("USERS")

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await asyncio.gather(
            self.users_db.update_many(
                {"chats": old_chat},
                {"$push": {"chats": new_chat}},
            ),
            self.users_db.update_many(
                {"chats": old_chat},
                {"$pull": {"chats": old_chat}},
            ),
            self.chats_db.update_one({"chat_id": old_chat}, {"$set": {"chat_id": new_chat}}),
        )

    async def on_chat_action(self, message: Message) -> None:
        """Delete user data from chats"""
        if message.new_chat_members:
            return

        chat = message.chat
        user = message.left_chat_member
        if user.id == self.bot.uid:
            await asyncio.gather(
                self.chats_db.delete_one({"chat_id": chat.id}),
                self.users_db.update_many(
                    {"chats": chat.id},
                    {"$pull": {"chats": chat.id}},
                ),
            )
        else:
            await asyncio.gather(
                self.users_db.update_one({"_id": user.id}, {"$pull": {"chats": chat.id}}),
                self.chats_db.update_one({"chat_id": chat.id}, {"$pull": {"member": user.id}}),
            )

    async def on_message(self, message: Message) -> None:
        """User database."""
        chat = message.chat
        user = message.from_user

        if not user or not chat:  # sanity check for service
            return

        await asyncio.gather(
            self.users_db.update_one(
                {"_id": user.id},
                {"$set": {"username": user.username}, "$addToSet": {"chats": chat.id}},
                upsert=True,
            ),
            self.chats_db.update_one(
                {"chat_id": chat.id},
                {"$set": {"chat_name": chat.title}, "$addToSet": {"member": user.id}},
                upsert=True,
            ),
        )

    async def cmd_info(self, ctx: command.Context, user: Optional[User] = None) -> Optional[str]:
        """Fetch user info"""
        chat = ctx.msg.chat

        if not user:
            return await self.text(chat.id, "err-peer-invalid")

        text = f"**{'Bot' if user.is_bot else 'User'} Info**\n"
        text += f"**ID:** `{user.id}`\n"
        text += f"**DC ID: **`{user.dc_id if user.dc_id else 'N/A'}`\n"
        text += f"**First Name: **{user.first_name}\n"
        if user.last_name:
            text += f"**Last Name: **{user.last_name}\n"
        text += f"**Username: **@{user.username}\n"
        text += f"**Permanent user link: **{user.mention}\n"
        text += (
            "**Number of profile pics: **"
            f"`{await self.bot.client.get_profile_photos_count(user.id)}`\n"
        )
        if user.status:
            text += f"**Last seen: ** `{user.status}`\n"
        if user.id in self.bot.staff:
            if user.id == self.bot.owner:
                text += "\nThis person is my **owner**!\nI would never do anything against him.\n"
            else:
                text += "\nThis person is one of my **Devs**!\nNearly as powerfull as my owner.\n"
        elif user.is_self:
            text += "\nI've seen them in every chats... wait it's me!!\nWow you're stalking me? 😂"
        user_db = await self.users_db.find_one({"_id": user.id})
        if user_db:
            text += f"\nI've seen them on {len(user_db['chats'])} chats."

        if user.photo:
            file = AsyncPath(await self.bot.client.download_media(user.photo.big_file_id))
            await self.bot.client.send_photo(chat.id, str(file), text)
            await file.unlink()
        else:
            await ctx.respond(text)
