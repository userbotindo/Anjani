""" Bot listener update decorator """
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
# pylint: disable=C0103

from typing import Callable, List, Optional, Union

from pyrogram.filters import Filter, create

from . import anjani as __bot__
from . import custom_filter


def on(
    cmd: Optional[Union[str, List[str]]] = "",
    filters: Optional[Filter] = None,
    admin_only: Optional[bool] = False,
    can_change_info: Optional[bool] = False,
    can_delete: Optional[bool] = False,
    can_restrict: Optional[bool] = False,
    can_invite_users: Optional[bool] = False,
    can_pin: Optional[bool] = False,
    can_promote: Optional[bool] = False,
    staff_only: Optional[bool] = False,
    group: Optional[int] = 0,
    update: Optional[str] = "command",
) -> callable:
    """Decorator for handling Update
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
        staff_only (`bool` | `str`, *optional*):
            Pass True if the command only used by all staff or pass the rank string
            if the command only available for those rank (eg: "owner" or "dev").
        update (`str`, *optional*):
            Option are [`command`, `message`, `callbackquery`].
            Pass one of the Options to use the update handler type.
            `command` -> `~Anjani.Client.on_command`,
            `message` -> `~Anjani.Client.on_message`,
            `callbackquery` -> `~Anjani.Client.on_callback_query`.
    """

    def listener_decorator(func: Callable) -> callable:
        if update == "command":
            _filters = custom_filter.command(commands=cmd)
            if filters:
                _filters = _filters & filters
        else:
            if filters:
                _filters = filters

        perm = (
            can_change_info
            or can_delete
            or can_restrict
            or can_invite_users
            or can_pin
            or can_promote
        )
        if perm:
            _filters = _filters & (
                create(
                    custom_filter.check_perm,
                    "CheckPermission",
                    can_change_info=can_change_info,
                    can_delete=can_delete,
                    can_restrict=can_restrict,
                    can_invite_users=can_invite_users,
                    can_pin=can_pin,
                    can_promote=can_promote,
                )
            )

        if admin_only:
            _filters = _filters & custom_filter.admin & custom_filter.bot_admin
        elif staff_only:
            if isinstance(staff_only, bool):
                _filters = _filters & custom_filter.staff
            elif isinstance(staff_only, str):
                _filters = _filters & create(
                    custom_filter.staff_rank, "CheckStaffRank", rank=staff_only
                )
            else:
                raise TypeError(
                    "staff_only arguments must be a string or bool not {}".format(type(staff_only))
                )

        if update == "command":
            dec = __bot__.client.on_command(filters=_filters, group=group)
        elif update == "message":
            dec = __bot__.client.on_message(filters=_filters, group=group)
        elif update == "callbackquery":
            dec = __bot__.client.on_callback_query(filters=_filters, group=group)

        return dec(func)

    return listener_decorator
