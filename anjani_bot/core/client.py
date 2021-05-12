"""Extend default Client"""
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
# pylint: disable=W0222

from typing import TYPE_CHECKING, Any, Callable, Optional, Union

import pyrogram
from pyrogram import ContinuePropagation, StopPropagation
from pyrogram.filters import Filter
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message

if TYPE_CHECKING:
    from .anjani import Anjani


class Client(pyrogram.Client):  # pylint: disable=too-many-ancestors
    """`~pyrogram.Client` overwrite decorator"""

    def __init__(self, bot: "Anjani", **kwargs: Any) -> None:
        self.__bot__ = bot

        super().__init__(**kwargs)

    async def __update__(
        self,
        func: Callable,
        message: Union[Message, CallbackQuery],
    ):
        func.__self__ = None

        # Get class of func itself
        for cls in list(self.__bot__.plugins.values()):
            if (
                str(cls).strip(">").split("from")[-1].strip().strip(".py").replace("/", ".")
                == func.__module__
                and not cls.disabled
            ):
                func.__self__ = cls
                break
        else:
            return

        func = getattr(func.__self__, func.__name__)
        try:
            await func(message)
        except (StopPropagation, ContinuePropagation):  # pylint: disable=try-except-raise
            raise

    def on_command(self, filters: Optional[Filter] = None, group: int = 0) -> callable:
        """Decorator for handling commands.

        Parameters:
            filters (:obj:`~pyrogram.filters`, *optional*):
                aditional build-in pyrogram filters to allow only a subset of messages to
                be passed in your function.

            group (`int`, *optional*):
                The group identifier, defaults to 0.
        """

        def decorator(func: Callable) -> callable:
            # Wrapper for decorator so func return `class` & `message`
            async def wrapper(_: Client, message: Message) -> None:
                return await self.__update__(func, message)

            self.add_handler(MessageHandler(wrapper, filters=filters), group)
            return func

        return decorator

    def on_message(self, filters: Optional[Filter] = None, group: int = 0) -> callable:
        """Decorator for handling messages.

        Parameters:
            filters (:obj:`~pyrogram.filters`, *optional*):
                Pass one or more filters to allow only a subset of messages to be passed
                in your function.

            group (``int``, *optional*):
                The group identifier, defaults to 0.
        """

        def decorator(func: Callable) -> callable:
            async def wrapper(_: Client, message: Message) -> None:
                return await self.__update__(func, message)

            self.add_handler(MessageHandler(wrapper, filters=filters), group)
            return func

        return decorator

    def on_callback_query(self, filters: Optional[Filter] = None, group: int = 0) -> callable:
        """Decorator for handling callback queries.

        Parameters:
            filters (:obj:`~pyrogram.filters`, *optional*):
                Pass one or more filters to allow only a subset of callback queries to be passed
                in your function.

            group (``int``, *optional*):
                The group identifier, defaults to 0.
        """

        def decorator(func: Callable) -> callable:
            async def wrapper(_: Client, query: CallbackQuery) -> None:
                return await self.__update__(func, query)

            self.add_handler(CallbackQueryHandler(wrapper, filters=filters), group)
            return func

        return decorator
