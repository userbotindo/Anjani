"""Anjani Plugin Base"""
# Copyright (C) 2020 - 2022  UserbotIndo Team, <https://github.com/userbotindo.git>
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
from typing import TYPE_CHECKING, Any, ClassVar, Coroutine, MutableMapping, Optional

from pyrogram.types import CallbackQuery, Message
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

    # { Anjani plugin base methods

    async def on_load(self) -> None:
        """Called when the plugin is loaded."""

    async def on_start(self, time_usec: int) -> None:
        """Called when the bot is started.

        Parameters:
            time_usec (`int`): Time in microseconds when the bot is started.
        """

    async def on_stop(self) -> None:
        """Called when the bot is stopped."""

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:  # type: ignore
        """Dispatched when /backup command is called in a group chat.

        parameters:
            chat_id (`int`): Id of the chat to backup.
        returns:
            `dict`: A dictionary that contains the data to be backed up.
        """

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        """Dispatched when /restore command is called in a group chat.

        parameters:
            chat_id (`int`): Id of the chat to restore.
            data (`dict`): A dictionary that contains the data to be restored.
        """

    # }

    # { Telegram event handler

    async def on_callback_query(self, query: CallbackQuery) -> None:
        """Called when the bot receives a callback query.

        Parameters:
            query (`CallbackQuery`): The callback query object.
        """

    async def on_message(self, message: Message) -> None:
        """Called when the bot receives a message.

        Parameters:
            message (`Message`): The message received.
        """

    async def on_chat_migrate(self, message: Message) -> None:
        """Called when a group chat is migrating to supergroup.

        Parameters:
            message (`Message`): Message object of the migrating chat.
        """

    async def on_chat_action(self, message: Message) -> None:
        """Called when a user join or leaves a chat.

        Parameters:
            message (`Message`): Message object of the chat action.
        """

    # }
