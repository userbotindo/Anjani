import asyncio
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Type

from pyrogram.types import Chat

if TYPE_CHECKING:
    from anjani.command import Context
    from anjani.core import Anjani


class BotAction:

    # Instances variable
    __running: bool
    __current: str
    __chat: Chat

    bot: "Anjani"
    loop: asyncio.AbstractEventLoop

    # Instance variable to be filled later
    __task: asyncio.Task[None]

    def __init__(self, ctx: "Context", action: str = "typing") -> None:
        self.__running = True
        self.__current = action
        self.__chat = ctx.chat

        self.bot = ctx.bot
        self.loop = ctx.bot.loop

    async def __cancel(self) -> None:
        await self.bot.client.send_chat_action(self.__chat.id, "cancel")

    async def __start(self) -> None:
        while self.__running:
            await self.bot.client.send_chat_action(self.__chat.id, self.__current)
            await asyncio.sleep(1)

    async def __stop(self) -> None:
        self.__running = False
        await self.__cancel()

        if not self.__task.done():
            self.__task.cancel()

    async def switch(self, action: str) -> None:
        """Switch current BotAction"""
        # avoid race condition with current action
        async with asyncio.Lock():
            await self.__cancel()
            self.__current = action

    def __enter__(self) -> "BotAction":
        self.__task = self.loop.create_task(self.__start())
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[Exception]],
        exc: Optional[Exception],
        tb: Optional[TracebackType]
    ) -> None:
        self.loop.create_task(self.__stop())

    async def __aenter__(self) -> "BotAction":
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[Type[Exception]],
        exc: Optional[Exception],
        tb: Optional[TracebackType]
    ) -> None:
        await self.__stop()
