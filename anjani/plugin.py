"""Anjani Plugin Base"""
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

import inspect
import logging
import os.path
from typing import TYPE_CHECKING, Any, ClassVar, Coroutine, Optional

from typing_extensions import final

from anjani.util.tg import get_text

if TYPE_CHECKING:
    from .core import Anjani


class Plugin:
    # Class variables
    name: ClassVar[str] = "Unnamed"
    disabled: ClassVar[bool] = False
    helpable: ClassVar[bool] = False

    # Instance variables
    bot: "Anjani"
    log: logging.Logger
    comment: Optional[str]

    def __init__(self, bot: "Anjani") -> None:
        self.bot = bot
        self.log = logging.getLogger(type(self).name.lower().replace(" ", "_"))
        self.comment = None

    # {
    # get_text and text can be declare as ClassVar but we don't do it
    # because we want to keep the documentation of the methods.

    @final
    def get_text(
        self,
        chat_id: Optional[int],
        text_name: str,
        *args: Any,
        noformat: bool = False,
        **kwargs: Any,
    ) -> Coroutine[Any, Any, str]:
        """Parse the string with user language setting.

        Parameters:
            chat_id (`int`, *Optional*):
                Id of the sender(PM's) or chat_id to fetch the user language setting.
                If chat_id is None, the language will always use 'en'.
            text_name (`str`):
                String name to parse. The string is parsed from YAML documents.
            *args (`any`, *Optional*):
                One or more values that should be formatted and inserted in the string.
                The value should be in order based on the language string placeholder.
            noformat (`bool`, *Optional*):
                If True, the text returned will not be formated.
                Default to False.
            **kwargs (`any`, *Optional*):
                One or more keyword values that should be formatted and inserted in the string.
                based on the keyword on the language strings.
        """
        return get_text(self.bot, chat_id, text_name, *args, noformat=noformat, **kwargs)

    # Convenient alias get_text method
    @final
    def text(
        self,
        chat_id: Optional[int],
        text_name: str,
        *args: Any,
        noformat: bool = False,
        **kwargs: Any,
    ) -> Coroutine[Any, Any, str]:
        """Parse the string with user language setting.

        Parameters:
            chat_id (`int`, *Optional*):
                Id of the sender(PM's) or chat_id to fetch the user language setting.
                If chat_id is None, the language will always use 'en'.
            text_name (`str`):
                String name to parse. The string is parsed from YAML documents.
            *args (`any`, *Optional*):
                One or more values that should be formatted and inserted in the string.
                The value should be in order based on the language string placeholder.
            noformat (`bool`, *Optional*):
                If True, the text returned will not be formated.
                Default to False.
            **kwargs (`any`, *Optional*):
                One or more keyword values that should be formatted and inserted in the string.
                based on the keyword on the language strings.
        """
        return get_text(self.bot, chat_id or 0, text_name, *args, noformat=noformat, **kwargs)

    # }

    @classmethod
    def format_desc(cls, comment: Optional[str] = None) -> str:
        _comment = comment + " " if comment else ""
        return f"{_comment}plugin '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"

    def __repr__(self) -> str:
        return "<" + self.format_desc(self.comment) + ">"
