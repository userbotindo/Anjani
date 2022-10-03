""" Canonical plugin for @dAnjani_bot """
# Copyright (C) 2020 - 2022  UserbotIndo Team, <https://github.com/userbotindo.git>
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
import re
from pathlib import Path
from typing import Any, ClassVar, MutableMapping

from pymongo.errors import PyMongoError
from pyrogram.enums.message_media_type import MessageMediaType
from pyrogram.types import Message

from anjani import listener, plugin, util

env = Path("config.env")
try:
    token = re.search(r'^(?!#)\s+?SP_TOKEN="(\w+)"', env.read_text().strip(), re.MULTILINE)
except (AttributeError, FileNotFoundError):
    token = ""

del env


class Canonical(plugin.Plugin):
    """Helper Plugin
    This plugin is only available for @dAnjani_bot
    to comunicate with https://userbotindo.com
    """

    name: ClassVar[str] = "Canonical"
    disabled: ClassVar[bool] = not token

    # Private
    __task: asyncio.Task[None]
    _mt: MutableMapping[MessageMediaType, str] = {
        MessageMediaType.STICKER: "s",
        MessageMediaType.PHOTO: "p",
        MessageMediaType.DOCUMENT: "f",
        MessageMediaType.VIDEO: "v",
    }

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("TEST")
        self.db_analytics = self.bot.db.get_collection("ANALYTICS")

    async def on_start(self, _: int) -> None:
        self.log.debug("Starting watch streams")
        self.__task = self.bot.loop.create_task(self.watch_streams())

    async def on_stop(self) -> None:
        self.log.debug("Stopping watch streams")
        self.__task.cancel()

    def get_type(self, message: Message) -> str:

        if message.media and message.media in self._mt:
            return self._mt[message.media]
        return "t"

    @listener.priority(65)
    async def on_message(self, message: Message) -> None:
        if message.outgoing:
            return

        today = util.time.sec()
        timestamp = today - (today % 86400)  # truncate to day
        await self.db_analytics.update_one(
            {"key": 2},
            {"$inc": {f"data.{str(timestamp)}.{self.get_type(message)}": 1}},
            upsert=True,
        )

    async def watch_streams(self) -> None:
        try:
            async with self.db.watch([{"$match": {"operationType": "insert"}}]) as stream:
                async for change in stream:
                    await self.dispatch_change(change["fullDocument"])
        except PyMongoError as e:
            self.log.error("Error", exc_info=e)

    async def dispatch_change(self, doc: MutableMapping[str, Any]) -> None:
        chat_id = doc["_id"]
        message = doc["message"]
        pin = doc.get("pin", False)
        disable_preview = doc.get("disable_preview", False)

        try:
            msg = await self.bot.client.send_message(
                chat_id=chat_id,
                text=message,
                disable_web_page_preview=disable_preview,
            )
            if pin:
                await self.bot.client.pin_chat_message(msg.chat.id, msg.id)
        except Exception as e:  # skipcq: PYL-W0703
            self.log.error(f"Error sending message to {chat_id}", exc_info=e)
        finally:
            await self.db.delete_one({"_id": chat_id})
