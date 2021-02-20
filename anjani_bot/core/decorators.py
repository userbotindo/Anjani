""" Bot decorator handlers """
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

from typing import Union, Optional, Callable, List

from pyrogram import Client, StopPropagation, ContinuePropagation
from pyrogram.filters import Filter, create
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery

from . import cust_filter
from .raw_client import RawClient
from .plugin_extender import UnknownPluginError


class Decorators(RawClient):
    # pylint: disable=signature-differs
    async def _mod(
            self,
            func: Callable,
            message: Union[Message, CallbackQuery]
    ):
        func.__self__ = None
        # Get class of func itself
        for _, cls in self.modules.items():
            if str(cls).strip(">").split("from")[-1].strip() == (
                    func.__module__.replace(".", "/") + ".py"):
                func.__self__ = cls
                break
        else:
            # for now raise for exception if func couldn't get the class itself
            raise UnknownPluginError("Uncaught plugin error...")

        try:
            await func(func.__self__, message)
        except (StopPropagation, ContinuePropagation):
            raise

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
            group: int = 0
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

            group (`int`, *optional*):
                The group identifier, defaults to 0.
        """

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

        def decorator(func: Callable) -> callable:
            # Wrapper for decorator so func return `class` & `message`
            async def wrapper(_: Client, message: Message) -> None:
                return await self._mod(func, message)

            self.add_handler(MessageHandler(wrapper, filters=_filters), group)
            return func

        return decorator

    def on_message(
            self,
            filters: Optional[Filter] = None,
            group: int = 0
    ) -> callable:
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
                return await self._mod(func, message)

            self.add_handler(MessageHandler(wrapper, filters=filters), group)
            return func

        return decorator

    def on_callback_query(
            self=None,
            filters=None,
            group: int = 0
    ) -> callable:
        """Decorator for handling callback queries.

        Parameters:
            filters (:obj:`~pyrogram.filters`, *optional*):
                Pass one or more filters to allow only a subset of callback queries to be passed
                in your function.

            group (``int``, *optional*):
                The group identifier, defaults to 0.
        """
        def decorator(func: Callable) -> callable:
            async def wrapper(_: Client, message: Message) -> None:
                return await self._mod(func, message)

            self.add_handler(CallbackQueryHandler(wrapper, filters=filters), group)
            return func

        return decorator
