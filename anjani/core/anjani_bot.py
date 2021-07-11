import asyncio
import logging
from typing import Optional

import aiohttp
import pyrogram

from anjani import custom_filter

from .database_provider import DataBase
from .command_dispatcher import CommandDispatcher
from .event_dispatcher import EventDispatcher
from .plugin_extenter import PluginExtender
from .telegram_bot import TelegramBot


class Anjani(TelegramBot,
             DataBase,
             PluginExtender,
             CommandDispatcher,
             EventDispatcher):
    # Initialized during instantiation
    log: logging.Logger
    http: aiohttp.ClientSession
    client: pyrogram.Client
    loop: asyncio.AbstractEventLoop
    stopping: bool

    def __init__(self):
        self.log = logging.getLogger("bot")
        self.loop = asyncio.get_event_loop()
        self.stopping = False

        # Initialize mixins
        super().__init__()

        # Initialize aiohttp session last in case another mixin fails
        self.http = aiohttp.ClientSession()

    @classmethod
    async def init_and_run(
        cls, *, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> "Anjani":
        anjani = None

        if loop:
            asyncio.set_event_loop(loop)

        try:
            anjani = cls()
            await anjani.run()
            return anjani
        finally:
            if anjani is None or (anjani is not None and not anjani.stopping):
                asyncio.get_event_loop().stop()

    async def stop(self) -> None:
        self.stopping = True

        self.log.info("Stopping")
        if self.loaded:
            await self.dispatch_event("stop")
            if self.client.is_connected:
                await self.client.stop()
        await self.http.close()
        await self.close_db()
        custom_filter.fetch_permissions.close()

        self.log.info("Running post-stop hooks")
        if self.loaded:
            await self.dispatch_event("stopped")