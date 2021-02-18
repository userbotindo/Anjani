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
from typing import Optional, Any, Awaitable, List, Union, MutableMapping, Dict

import aiohttp
from pyrogram import Client, idle
from pyrogram.filters import Filter, create

from . import cust_filter, pool
from .database import DataBase
from .plugin_extender import PluginExtender
from .. import plugin
from ..config import Config
from ..utils import get_readable_time

LOGGER = logging.getLogger(__name__)


class Anjani(Client, DataBase, PluginExtender):  # pylint: disable=too-many-ancestors
    """ AnjaniBot Client """
    # pylint: disable=too-many-instance-attributes
    http: aiohttp.ClientSession
    identifier: int
    modules: MutableMapping[str, plugin.Plugin]
    name: str
    queue: asyncio.queues.Queue
    staff: Dict[str, Union[str, int]]
    username: str

    def __init__(self, **kwargs):
        kwargs = {
            "api_id": Config.API_ID,
            "api_hash": Config.API_HASH,
            "bot_token": Config.BOT_TOKEN,
            "session_name": ":memory:",
        }
        self.modules = {}
        self.staff = {"owner": Config.OWNER_ID}

        try:
            import uvloop
        except ImportError:
            pass
        else:
            uvloop.install()
        self.queue = asyncio.Queue()

        self._start_time = time.time()
        self._log_channel = Config.LOG_CHANNEL

        super().__init__(**kwargs)

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

    @property
    def staff_id(self) -> List[int]:
        """ Get bot staff ids as a list """
        _id = [self.staff.get("owner")]
        _id.extend(self.staff.get("dev") + self.staff.get("sudo"))
        return _id

    async def _load_all_attribute(self) -> None:
        """ Load all client attributes """
        bot = await self.get_me()
        self.identifier = bot.id
        self.username = bot.username
        if bot.last_name:
            self.name = bot.first_name + " " + bot.last_name
        else:
            self.name = bot.first_name

        _db = self.get_collection("STAFF")
        self.staff.update({'dev': [], 'sudo': []})
        async for i in _db.find():
            self.staff[i["rank"]].append(i["_id"])

    async def _start(self):
        """ Start client """
        LOGGER.info("Starting Bot Client...")
        pool.start(self.queue)
        await self.connect_db("AnjaniBot")
        self._load_language()
        submodules = [
            importlib.import_module("anjani_bot.plugins." + info.name, __name__)
            for info in pkgutil.iter_modules(["anjani_bot/plugins"])
        ]
        self.load_all_modules(submodules)
        await super().start()
        await self._load_all_attribute()
        await self.channel_log("Bot started successfully...")

    async def _stop(self):
        """ Stop client """
        LOGGER.info("Disconnecting...")
        await super().stop()
        await self.http.close()
        await self.disconnect_db()
        await pool.stop(self.queue)

    def begin(self) -> None:
        """Start AnjaniBot"""
        lock = asyncio.Lock()
        tasks: List[asyncio.Task] = []

        async def finalized() -> None:
            async with lock:
                for task in tasks:
                    task.cancel()
                if self.is_initialized:
                    await self._stop()
                # pylint: disable=expression-not-assigned
                [t.cancel() for t in asyncio.all_tasks() if t is not asyncio.current_task()]
                await self.loop.shutdown_asyncgens()
                self.loop.stop()
                LOGGER.info("Loop stopped")

        async def shutdown(sig: signal.Signals) -> None:
            LOGGER.info("Received Stop Signal [%s], Exiting...", sig.name)
            await finalized()

        for sig in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
            self.loop.add_signal_handler(
                sig, lambda sig=sig: self.loop.create_task(shutdown(sig)))

        self.loop.run_until_complete(self._start())

        try:
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
            staff_only: Optional[Union[bool, str]] = False,
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

            staff_only (`bool` | 'str', *optional*):
                Pass True if the command only used by all staff or pass the rank string
                if the command only available for those rank.
                Eg: "owner" or "dev"
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
                if isinstance(staff_only, bool):
                    _filters = _filters & cust_filter.staff
                else:
                    _filters = _filters & create(
                        cust_filter.staff_rank,
                        "CheckStaffRank",
                        rank=staff_only
                    )

            dec = self.on_message(filters=_filters)
            return dec(coro)
        return decorator

    async def channel_log(
            self,
            text: str,
            parse_mode: Optional[str] = object,
            disable_web_page_preview: bool = None,
            disable_notification: bool = None,
            reply_markup: Union[
                "types.InlineKeyboardMarkup",
                "types.ReplyKeyboardMarkup",
                "types.ReplyKeyboardRemove",
                "types.ForceReply"
            ] = None
        ) -> Union["types.Message", None]:
        """Shortcut method to send message to log channel.

        Parameters:
            text (`str`):
                Text of the message to be sent.

            parse_mode (`str`, *optional*):
                By default, texts are parsed using both Markdown and HTML styles.
                You can combine both syntaxes together.
                Pass "markdown" or "md" to enable Markdown-style parsing only.
                Pass "html" to enable HTML-style parsing only.
                Pass None to completely disable style parsing.

            disable_web_page_preview (`bool`, *optional*):
                Disables link previews for links in this message.

            disable_notification (`bool`, *optional*):
                Sends the message silently.
                Users will receive a notification with no sound.

            reply_markup (
                :obj:`~InlineKeyboardMarkup` | :obj:`~ReplyKeyboardMarkup` |
                :obj:`~ReplyKeyboardRemove` | :obj:`~ForceReply`, *optional*
                ):
                Additional interface options. An object for an inline keyboard,
                custom reply keyboard, instructions to remove reply keyboard or
                to force a reply from the user.

        Returns:
            :obj:`~types.Message`: On success, the sent text message is returned.
        """
        if self._log_channel == 0:
            LOGGER.warning("No LOG_CHANNEL var! message '%s' not sended.", text)
            return None

        return await self.send_message(
            chat_id=self._log_channel,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            reply_markup=reply_markup
        )
