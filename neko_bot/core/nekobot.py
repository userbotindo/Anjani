"""Bot core client"""

import asyncio
import importlib
import logging
import signal
from typing import Optional, Any, Awaitable, List, Union

from pyrogram import Client, idle
from pyrogram.filters import Filter

from . import cust_filter, pool, DataBase
from .. import Config
from ..plugins import ALL_MODULES

LOGGER = logging.getLogger(__name__)


class NekoBot(DataBase, Client):  # pylint: disable=too-many-ancestors
    """ NekoBot Client """

    def __init__(self, **kwargs):
        LOGGER.info("Setting up bot client...")
        kwargs = {
            "api_id" : Config.API_ID,
            "api_hash" : Config.API_HASH,
            "bot_token" : Config.BOT_TOKEN,
            "session_name" : ":memory:",
        }
        super().__init__(**kwargs)

    async def start(self):
        """ Start client """
        pool.start()
        await self.connect_db("NekoBot")
        LOGGER.info("Importing available modules")
        for mod in ALL_MODULES:
            imported_module = importlib.import_module("neko_bot.plugins." + mod)
            if hasattr(
                    imported_module,
                    "__MODULE__"
                ) and imported_module.__MODULE__:
                imported_module.__MODULE__ = imported_module.__MODULE__
                LOGGER.debug("%s module loaded", mod)
        LOGGER.info("Starting Bot Client...")
        await super().start()

    async def stop(self):  # pylint: disable=arguments-differ
        """ Stop client """
        LOGGER.info("Disconnecting...")
        await super().stop()
        await self.disconnect_db()
        await pool.stop()

    def begin(self, coro: Optional[Awaitable[Any]] = None) -> None:
        """Start NekoBot"""

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
