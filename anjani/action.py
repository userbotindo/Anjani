import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anjani.command import Context


class BotAction:
    context: "Context"
    action: str
    loop: asyncio.AbstractEventLoop

    def __init__(self, ctx: "Context", action: str = "typing"):
        self.context = ctx
        self.action = action

        self.loop = ctx.bot.loop

    async def do_action(self):
        chat = self.context.chat
        send = self.context.bot.client.send_chat_action

        while True:
            await send(chat.id, self.action)
            await asyncio.sleep(1)

    async def cancel(self):
        chat = self.context.chat
        send = self.context.bot.client.send_chat_action
        await send(chat.id, "cancel")

    def __enter__(self):
        self.task = self.loop.create_task(self.do_action())
        return self

    def __exit__(self, exc_type, exc, tb):
        self.task.cancel()
        self.loop.create_task(self.cancel())

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb):
        self.task.cancel()
        await self.cancel()
