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

# pylint: disable=unsubscriptable-object

import asyncio
import importlib
import json
import logging
import signal
import time
from typing import Optional, Any, Awaitable, List, Union

from pyrogram import Client, idle
from pyrogram.filters import Filter

from . import cust_filter, pool, DataBase
from .. import Config
from ..plugins import ALL_MODULES
from ..utils import get_readable_time

LOGGER = logging.getLogger(__name__)


class Anjani(Client, DataBase):  # pylint: disable=too-many-ancestors
    """ AnjaniBot Client """
    staff = dict()

    def __init__(self, **kwargs):
        LOGGER.info("Setting up bot client...")
        kwargs = {
            "api_id" : Config.API_ID,
            "api_hash" : Config.API_HASH,
            "bot_token" : Config.BOT_TOKEN,
            "session_name" : ":memory:",
        }
        self._start_time = time.time()
        self.staff["owner"] = Config.OWNER_ID
        super().__init__(**kwargs)

    def __str__(self):
        return f"Uptime: {self.uptime}\nStaff list:\n{json.dumps(self.staff, indent=2)}"

    @property
    def uptime(self) -> str:
        """ Get bot uptime """
        return get_readable_time(time.time() - self._start_time)

    @property
    def staff_id(self) -> List[int]:
        """ Get bot staff ids as a list """
        _id = [self.staff.get("owner")]
        _id.extend(self.staff.get("dev") + self.staff.get("sudo"))
        return _id

    async def _load_all_attribute(self) -> None:
        """ Load all client attributes """
        # pylint: disable=attribute-defined-outside-init
        bot = await self.get_me()
        self.id = bot.id  # pylint: disable = C0103
        self.username = bot.username
        if bot.last_name:
            self.name = bot.first_name + " " + bot.last_name
        else:
            self.name = bot.first_name

        _db = self.get_collection("STAFF")
        self.staff.update({'dev': [], 'sudo': []})
        async for i in _db.find():
            self.staff[i["rank"]].append(i["_id"])

    async def start(self):
        """ Start client """
        pool.start()
        await self.connect_db("AnjaniBot")
        self._load_language()
        LOGGER.info("Importing available modules")
        for mod in ALL_MODULES:
            imported_module = importlib.import_module("anjani_bot.plugins." + mod)
            if hasattr(
                    imported_module,
                    "__MODULE__"
                ) and imported_module.__MODULE__:
                imported_module.__MODULE__ = imported_module.__MODULE__
                LOGGER.debug("%s module loaded", mod)
        LOGGER.info("Starting Bot Client...")
        await super().start()
        await self._load_all_attribute()

    async def stop(self):  # pylint: disable=arguments-differ
        """ Stop client """
        LOGGER.info("Disconnecting...")
        await super().stop()
        await self.disconnect_db()
        await pool.stop()

    def begin(self, coro: Optional[Awaitable[Any]] = None) -> None:
        """Start AnjaniBot"""

        lock = asyncio.Lock()
        tasks: List[asyncio.Task] = []

        async def finalized() -> None:
            async with lock:
                for task in tasks:
                    task.cancel()
                if self.is_initialized:
                    await self.stop()
                # pylint: disable=expression-not-assigned
                [t.cancel() for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                await self.loop.shutdown_asyncgens()
                self.loop.stop()
                LOGGER.info("Loop stopped")

        async def shutdown(sig: signal.Signals) -> None:  # pylint: disable=no-member
            LOGGER.info("Received Stop Signal [%s], Exiting...", sig.name)
            await finalized()

        for sig in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
            self.loop.add_signal_handler(
                sig, lambda sig=sig: self.loop.create_task(shutdown(sig)))

        self.loop.run_until_complete(self.start())

        try:
            if coro:
                LOGGER.info("Running Coroutine")
                self.loop.run_until_complete(coro)
            else:
                LOGGER.info("Idling")
                idle()
            self.loop.run_until_complete(finalized())
        except (asyncio.CancelledError, RuntimeError):
            pass
        finally:
            self.loop.close()
            LOGGER.info("Loop closed")

    def on_command(  # pylint: disable=too-many-arguments
            self,
            cmd: Union[str, List[str]],
            filters: Optional[Filter] = None,
            admin: Optional[bool] = False,
            staff: Optional[bool] = False,
            group: Optional[int] = 0,
        ) -> callable:
        """Decorator for handling commands

        Parameters:
            cmd (`str` | List of `str`):
                Pass one or more commands to trigger your function.

            filters (:obj:`~pyrogram.filters`, *optional*):
                aditional build-in pyrogram filters to allow only a subset of messages to
                be passed in your function.

            admin (`bool`, *optional*):
                Pass True if the command only used by admins (bot staff included).
                The bot need to be an admin as well. This parameters also means
                that the command won't run in private (PM`s).

            staff (`bool`, *optional*):
                Pass True if the command only used by Staff (SUDO and OWNER).

            group (`int`, *optional*):
                The group identifier, defaults to 0.
        """

        def decorator(coro):
            _filters = cust_filter.command(commands=cmd)
            if filters:
                _filters = _filters & filters

            if admin:
                _filters = _filters & cust_filter.admin & cust_filter.bot_admin
            elif staff:
                _filters = _filters & cust_filter.staff

            dec = self.on_message(filters=_filters, group=group)
            return dec(coro)
        return decorator
