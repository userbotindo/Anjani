"""Anjani example-plugin"""
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
import io
import sys
from typing import IO, Any, ClassVar, MutableMapping

if sys.version_info >= (3, 10):
    from aiopath import AsyncPurePosixPath as PosixPath
else:
    from aiopath import PureAsyncPosixPath as PosixPath

from pyrogram.types import CallbackQuery, Message

from anjani import command, filters, listener, plugin, util


class ExamplePlugin(plugin.Plugin):
    name: ClassVar[str] = "Example"
    disabled: ClassVar[bool] = True
    helpable: ClassVar[bool] = False

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("example")

    # Filter Listener only on group chats
    @listener.filters(filters.group)
    async def on_message(self, message: Message) -> None:
        self.log.info(f"Received message: {message.text}")
        await self.db.update_one({"_id": message.id}, {"$set": {"text": message.text}}, upsert=True)

    async def on_callback_query(self, query: CallbackQuery) -> None:
        self.log.info("Button clicked: %s", query.data)
        await query.answer("You clicked the button!")

    async def on_chat_action(self, message: Message) -> None:
        if message.new_chat_members:
            for new_member in message.new_chat_members:
                self.log.info("New member joined: %s", new_member.first_name)
        else:
            left_member = message.left_chat_member
            self.log.info("A member just left chat: %s", left_member.first_name)

    async def on_chat_migrate(self, message: Message) -> None:
        self.log.info("Migrating chat...")
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        """Dispatched when /backup command is Called"""
        self.log.info("Backing up data plugin: %s", self.name)
        data = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        if not data:
            return {}

        return {self.name: data}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        """Dispatched when /restore command is Called"""
        self.log.info("Restoring data plugin: %s", self.name)
        await self.db.update_one({"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True)

    async def cmd_test(self, ctx: command.Context) -> str:
        await ctx.respond("Processing...")
        await asyncio.sleep(1)

        if ctx.input:
            return ctx.input

        return "It works!"

    async def get_cat(self) -> IO[bytes]:
        # Get the link to a random cat picture
        async with self.bot.http.get("https://aws.random.cat/meow") as resp:
            # Read and parse the response as JSON
            json = await resp.json()
            # Get the "file" field from the parsed JSON object
            cat_url = json["file"]

        # Get the actual cat picture
        async with self.bot.http.get(cat_url) as resp:
            # Get the data as a byte array (bytes object)
            cat_data = await resp.read()

        # Construct a byte stream from the data.
        # This is necessary because the bytes object is immutable, but we need to add a "name" attribute to set the
        # filename. This facilitates the setting of said attribute without altering behavior.
        cat_stream = io.BytesIO(cat_data)

        # Set the name of the cat picture before sending.
        # This is necessary for Pyrogram to detect the file type and send it as a photo/GIF rather than just a plain
        # unnamed file that doesn't render as media in clients.
        # We abuse aiopath to extract the filename section here for convenience, since URLs are *mostly* POSIX paths
        # with the exception of the protocol part, which we don't care about here.
        cat_stream.name = PosixPath(cat_url).name

        return cat_stream

    # Filter Command only on private
    # And create alias command /get_cat
    @command.filters(filters.private, aliases=["get_cat"])
    async def cmd_cat(self, ctx: command.Context) -> None:
        await ctx.respond("Fetching cat...")
        cat_stream = await self.get_cat()

        await ctx.respond(photo=cat_stream)
