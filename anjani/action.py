"""Anjani base chat action"""
# Copyright (C) 2020 - 2023  UserbotIndo Team, <https://github.com/userbotindo.git>
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
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Type

from pyrogram.enums.chat_action import ChatAction
from pyrogram.errors import FloodWait
from pyrogram.types import Chat

if TYPE_CHECKING:
    from anjani.command import Context
    from anjani.core import Anjani


class BotAction:

    # Instances variable
    __running: bool
    __current: ChatAction
    __chat: Chat

    bot: "Anjani"
    loop: asyncio.AbstractEventLoop

    # Instance variable to be filled later
    __task: asyncio.Task[None]

    def __init__(self, ctx: "Context", action: ChatAction = ChatAction.TYPING) -> None:
        self.__running = True
        self.__current = action
        self.__chat = ctx.chat

        self.bot = ctx.bot
        self.loop = ctx.bot.loop

    async def __cancel(self) -> None:
        try:
            await self.bot.client.send_chat_action(self.__chat.id, ChatAction.CANCEL)
        except FloodWait as e:
            await asyncio.sleep(e.value)  # type: ignore

    async def __start(self) -> None:
        while self.__running:
            try:
                await self.bot.client.send_chat_action(self.__chat.id, self.__current)
            except FloodWait as e:
                await asyncio.sleep(e.value)  # type: ignore
            else:
                await asyncio.sleep(1)

    async def __stop(self) -> None:
        self.__running = False
        await self.__cancel()

        if not self.__task.done():
            self.__task.cancel()
        else:
            self.__task.result()

    async def switch(self, action: ChatAction) -> None:
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
        tb: Optional[TracebackType],
    ) -> None:
        self.loop.create_task(self.__stop())

    async def __aenter__(self) -> "BotAction":
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[Type[Exception]],
        exc: Optional[Exception],
        tb: Optional[TracebackType],
    ) -> None:
        await self.__stop()
