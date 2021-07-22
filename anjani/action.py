import asyncio
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Type

if TYPE_CHECKING:
    from anjani.command import Context


class BotAction:
    context: "Context"
    action: str
    loop: asyncio.AbstractEventLoop

    def __init__(self, ctx: "Context", action: str = "typing") -> None:
        self.context = ctx
        self.action = action

        self.loop = ctx.bot.loop

    async def do_action(self) -> None:
        chat = self.context.chat
        send = self.context.bot.client.send_chat_action

        while True:
            await send(chat.id, self.action)
            await asyncio.sleep(1)

    async def cancel(self) -> None:
        chat = self.context.chat
        send = self.context.bot.client.send_chat_action
        await send(chat.id, "cancel")

    def __enter__(self) -> "BotAction":
        self.task = self.loop.create_task(self.do_action())
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[Exception]],
        exc: Optional[Exception],
        tb: Optional[TracebackType]
    ) -> None:
        self.task.cancel()
        self.loop.create_task(self.cancel())

    async def __aenter__(self) -> "BotAction":
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[Type[Exception]],
        exc: Optional[Exception],
        tb: Optional[TracebackType]
    ) -> None:
        self.task.cancel()
        await self.cancel()
