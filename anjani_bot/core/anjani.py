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
from typing import List, Optional

import aiohttp
import aiorun
import pyrogram

from ..utils import get_readable_time
from . import pool
from .database import DataBase
from .plugin_extender import PluginExtender  # pylint: disable=R0401
from .telegram_bot import TelegramBot  # pylint: disable=R0401

LOGGER = logging.getLogger(__name__)


class Anjani(TelegramBot, DataBase, PluginExtender):
    """ AnjaniBot Client """
    client: pyrogram.Client
    http: aiohttp.ClientSession
    loop: asyncio.AbstractEventLoop

    def __init__(self):
        self.stopping = False

        self._start_time = time.time()

        # Init Base
        super().__init__()

    def __str__(self):
        output = f"Name : {self.name}\n"
        output += f"Username : {self.username}\n"
        output += f"ID : {self.identifier}\n"
        output += f"Uptime: {self.uptime}\n"
        output += f"Pyrogram: {self.client.app_version}\n"
        output += f"Language: {self.language}\n"
        output += f"Loaded Plugins:{json.dumps(list(self.plugins.keys()), indent=2)}\n"
        output += f"Staff list:{json.dumps(self.staff, indent=2)}\n"
        return output

    @property
    def uptime(self) -> str:
        """ Get bot uptime """
        return get_readable_time(time.time() - self._start_time)

    async def begin(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> "Anjani":
        """Start AnjaniBot"""
        if loop:
            asyncio.set_event_loop(loop)
            self.loop = loop

        # Initialize aiohttp inside coro because in __init__
        # will raise RuntimeError
        self.http = aiohttp.ClientSession()

        try:
            await self.run()
        except (asyncio.exceptions.CancelledError, RuntimeError):
            pass
        finally:
            if not self.stopping:
                LOGGER.info("Loop stopped")
                self.loop.stop()

    async def stop(self) -> None:
        """ Stop client """
        LOGGER.info("Disconnecting...")

        self.stopping = True

        await self.http.close()
        await self.disconnect_db()

        async def finalize() -> None:
            lock = asyncio.Lock()
            running_tasks: List[asyncio.Task] = []

            async with lock:
                for task in running_tasks:
                    task.cancel()
                if self.client.is_initialized:
                    await self.client.stop()
                else:
                    pool.stop()
                for task in asyncio.all_tasks():
                    if task is not asyncio.current_task():
                        task.cancel()
                await self.loop.shutdown_asyncgens()
                self.loop.stop()
        await aiorun.shutdown_waits_for(finalize())
