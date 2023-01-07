"""Anjani Errors Constructor"""
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

from typing import TYPE_CHECKING, Any, Optional, Type

if TYPE_CHECKING:
    from .command import Command
    from .plugin import Plugin
    from .util.converter import Converter

__all__ = [
    "AnjaniException",
    "BackupError",
    "BadArgument",
    "BadBoolArgument",
    "BadResult",
    "CommandHandlerError",
    "CommandInvokeError",
    "ConversionError",
    "EventDispatchError",
    "ExistingCommandError",
    "ExistingPluginError",
    "PluginLoadError",
]


class AnjaniException(Exception):
    """Base exception class for Anjani"""


class BackupError(AnjaniException):
    """Unexpected backup data type"""


class EventDispatchError(AnjaniException):
    """Exception raised when a dispatcher raised an exception"""


class CommandHandlerError(AnjaniException):
    """Exception raised when the command handler raised an exception."""


class CommandInvokeError(AnjaniException):
    """Exception raised when the command being invoked raised an exception."""


class PluginLoadError(AnjaniException):
    """Base exception class for every Plugin errors"""


class BadArgument(AnjaniException):
    """Exception that raised when parsing or converting argument encountered a failure."""


class ConversionError(BadArgument):
    """Base exception class for any argument conversion errors

    Attributes:
        converter (`Converter`): The converter instance that failed.
        origin (`Exception`): The original exception that was raised.
    """

    def __init__(  # skipcq: PYL-W1113
        self, converter: Optional["Converter"] = None, err: Optional[Exception] = None, *args: Any
    ) -> None:
        if converter and err:
            self.converter = type(converter).__name__
            self.origin = err
            super().__init__(f"Failed to convert on '{self.converter}', {err}")
        else:
            super().__init__(*args)


class BadBoolArgument(ConversionError):
    """Exception that raised when a bool argument can't be converted"""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)


class BadResult(ConversionError):
    """Exception that raised when an argument results is not a valid types"""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)


class ExistingCommandError(PluginLoadError):
    """Exception that raised when a command registered more then one.

    Attributes:
        old_cmd (:obj:`Command`): The old command that already registered.
        new_cmd (:obj:`Command`): The new command that already registered.
        alias (:obj:`bool`): Wether the command is an alias or not.
    """

    def __init__(self, old_cmd: "Command", new_cmd: "Command", alias: bool = False) -> None:
        al_str = "alias of " if alias else ""
        old_name = type(old_cmd.plugin).__name__
        new_name = type(new_cmd.plugin).__name__
        self.old_cmd = old_cmd
        self.new_cmd = new_cmd
        self.alias = alias
        super().__init__(
            f"Attempt to replace existing command '{old_cmd.name}' (from {old_name}) with {al_str}'{new_cmd.name}' (from {new_name})"
        )


class ExistingPluginError(PluginLoadError):
    """Exception that raised when two same Plugin name registered.

    Attributes:
        old_plugin (:obj:`Plugin`): The old plugin that already registered.
        new_plugin (:obj:`Plugin`): The new plugin that already registered.
        alias (:obj:`bool`): Wether the command is an alias or not.
    """

    def __init__(self, old_plugin: Type["Plugin"], new_plugin: Type["Plugin"]) -> None:
        self.old_plugin = old_plugin
        self.new_plugin = new_plugin
        super().__init__(f"Plugin '{old_plugin.name}' ({old_plugin.__name__}) already exists")
