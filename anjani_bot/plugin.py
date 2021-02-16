"""Bot Plugin"""
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


import inspect
import logging
import os.path

from typing import (
    ClassVar,
    List,
    Optional
)

from pyrogram.types import InlineKeyboardButton


class Plugin:
    # Class variables
    name: ClassVar[str] = "Unnamed"
    disabled: ClassVar[bool] = False

    # Instance variables
    log: logging.Logger
    comment: Optional[str]

    def __init__(self, bot) -> None:
        self.bot = bot
        self.log = logging.getLogger(type(self).name.lower().replace(" ", "_"))
        self.comment = None

    @classmethod
    def format_desc(cls, comment: Optional[str] = None):
        """ module description """
        _comment = comment + " " if comment else ""
        return (f"{_comment}plugin {cls.name} ({cls.__name__}) "
                f"from {os.path.relpath(inspect.getfile(cls))}")

    def __repr__(self):
        return f"< {self.format_desc(self.comment)} >"


async def help_builder(module_list: list, prefix: str) -> List:
    """ Build the help button """
    modules = [
        InlineKeyboardButton(
            # await self.text(chat_id, f"{x.name.lower()}_button"),
            x.name,
            callback_data="{}_module({})".format(prefix, x.name.lower()))
        for x in module_list
    ]

    pairs = [
        modules[i * 3:(i + 1) * 3]
        for i in range((len(modules) + 3 - 1) // 3)
    ]
    return pairs
