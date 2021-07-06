"""Anjani Errors Constructor"""
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


__all__ = ["AnjaniException", "BackupError", "CommandHandlerError", "CommandInvokeError"]


class AnjaniException(Exception):
    """Base exception class for Anjani"""


class BackupError(AnjaniException):
    """Unexpected backup data type"""


class CommandHandlerError(AnjaniException):
    """Exception raised when the command handler raised an exception."""


class CommandInvokeError(AnjaniException):
    """Exception raised when the command being invoked raised an exception."""
