"""Bot core client"""
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
import json
import logging
import time
from typing import Dict, Optional, Union

import aiohttp

import pyrogram

from .database import DataBase
from .plugin_extender import PluginExtender
from .telegram_bot import TelegramBot
from ..config import Config
from ..utils import get_readable_time

LOGGER = logging.getLogger(__name__)


class Anjani(DataBase, PluginExtender, TelegramBot):  # pylint: disable=too-many-ancestors
    """ AnjaniBot Client """
    # pylint: disable=too-many-instance-attributes
    client: pyrogram.Client
    http: aiohttp.ClientSession
    identifier: int
    loop: asyncio.AbstractEventLoop
    name: str
    queue: asyncio.queues.Queue
    staff: Dict[str, Union[str, int]]
    stopping: bool
    username: str

    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue()
        self.stopping = False

        self._start_time = time.time()
        self._log_channel = Config.LOG_CHANNEL

        super().__init__()

        # Initialized aiohttp last in case bot failed to init
        self.http = aiohttp.ClientSession()

    def __str__(self):
        output = f"Name : {self.name}\n"
        output += f"Username : {self.username}\n"
        output += f"ID : {self.identifier}\n"
        output += f"Uptime: {self.uptime}\n"
        output += f"Pyrogram: {self.app_version}\n"
        output += f"Language: {self.language}\n"
        output += f"Loaded Modules:{json.dumps(self.loaded, indent=2)}\n"
        output += f"Staff list:{json.dumps(self.staff, indent=2)}\n"
        return output

    @property
    def uptime(self) -> str:
        """ Get bot uptime """
        return get_readable_time(time.time() - self._start_time)

    def begin(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> "Anjani":
        """Start AnjaniBot"""
        if loop:
            asyncio.set_event_loop(loop)

        try:
            self.loop.run_until_complete(self.run())
        finally:
            if not self.stopping:
                LOGGER.info("Loop stopped")
                asyncio.get_event_loop().stop()

    async def stop(self) -> None:
        """ Stop client """
        LOGGER.info("Disconnecting...")

        self.stopping = True

        if self.client.is_initialized:
            await self.client.stop()
        await self.http.close()
        await self.disconnect_db()
