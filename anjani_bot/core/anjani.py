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
import importlib
import pkgutil
import json
import logging
import signal
import time
from types import ModuleType
from typing import Optional, Any, Awaitable, List, Union, Iterable

import aiohttp
from pyrogram import Client, idle
from pyrogram.filters import Filter, create

from . import cust_filter, pool, DataBase
from .plugin_extender import PluginExtender
from .. import Config
from ..utils import get_readable_time

LOGGER = logging.getLogger(__name__)


class Anjani(Client, DataBase, PluginExtender):  # pylint: disable=too-many-ancestors
    """ AnjaniBot Client """
    staff = dict()
    submodules: Iterable[ModuleType]
    http: aiohttp.ClientSession

    def __init__(self, **kwargs):
        LOGGER.info("Setting up bot client...")
        kwargs = {
            "api_id": Config.API_ID,
            "api_hash": Config.API_HASH,
            "bot_token": Config.BOT_TOKEN,
            "session_name": ":memory:",
        }
        self.http = aiohttp.ClientSession()
        self.modules = {}
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
        LOGGER.info("Starting Bot Client...")
        self.submodules = [
            importlib.import_module("anjani_bot.plugins." + info.name, __name__)
            for info in pkgutil.iter_modules(["anjani_bot/plugins"])
        ]
        self.load_all_modules(self.submodules)
        await super().start()
        await self._load_all_attribute()

    async def stop(self):  # pylint: disable=arguments-differ
        """ Stop client """
        LOGGER.info("Disconnecting...")
        await super().stop()
        await self.http.close()
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

    def on_command(
            self,
            cmd: Union[str, List[str]],
            filters: Optional[Filter] = None,
            admin_only: Optional[bool] = False,
            can_change_info: Optional[bool] = False,
            can_delete: Optional[bool] = False,
            can_restrict: Optional[bool] = False,
            can_invite_users: Optional[bool] = False,
            can_pin: Optional[bool] = False,
            can_promote: Optional[bool] = False,
            staff_only: Optional[bool] = False,
        ) -> callable:
        """Decorator for handling commands

        Parameters:
            cmd (`str` | List of `str`):
                Pass one or more commands to trigger your function.

            filters (:obj:`~pyrogram.filters`, *optional*):
                aditional build-in pyrogram filters to allow only a subset of messages to
                be passed in your function.

            admin_only (`bool`, *optional*):
                Pass True if the command only used by admins (bot staff included).
                The bot need to be an admin as well. This parameters also means
                that the command won't run in private (PM`s).

            can_change_info (`bool`, *optional*):
                check if user and bot can change the chat title, photo and other settings.
                default False.

            can_delete (`bool`, *optional*):
                check if user and bot can delete messages of other users.
                default False

            can_restrict (`bool`, *optional*):
                check if user and bot can restrict, ban or unban chat members.
                default False.

            can_invite_users (`bool`, *optional*):
                check if user and bot is allowed to invite new users to the chat.
                default False.

            can_pin (`bool`, *optional*):
                check if user and bot is allowed to pin messages.
                default False.

            can_promote (`bool`, *optional*):
                check if user and bot can add new administrator.
                default False

            staff_only (`bool`, *optional*):
                Pass True if the command only used by Staff (SUDO and OWNER).
        """

        def decorator(coro):
            _filters = cust_filter.command(commands=cmd)
            if filters:
                _filters = _filters & filters

            perm = (can_change_info or can_delete or
                    can_restrict or can_invite_users or
                    can_pin or can_promote)
            if perm:
                _filters = _filters & (
                    create(
                        cust_filter.check_perm,
                        "CheckPermission",
                        can_change_info=can_change_info,
                        can_delete=can_delete,
                        can_restrict=can_restrict,
                        can_invite_users=can_invite_users,
                        can_pin=can_pin,
                        can_promote=can_promote
                    )
                )

            if admin_only:
                _filters = _filters & cust_filter.admin & cust_filter.bot_admin
            elif staff_only:
                _filters = _filters & cust_filter.staff

            dec = self.on_message(filters=_filters)
            return dec(coro)
        return decorator
