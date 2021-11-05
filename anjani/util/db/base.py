"""Anjani database core"""
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

from typing import TYPE_CHECKING, Any, Union

from bson import CodecOptions
from pymongo import MongoClient
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.command_cursor import CommandCursor, RawBatchCommandCursor
from pymongo.cursor import Cursor, RawBatchCursor
from pymongo.database import Database
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import _ServerMode
from pymongo.write_concern import WriteConcern

if TYPE_CHECKING:
    from .command_cursor import _LatentCursor


class AsyncBase:
    """Base Class for AsyncIOMongoDB Instances"""

    dispatch: Union[
        "_LatentCursor",
        ClientSession,
        Collection,
        CommandCursor,
        Cursor,
        Database,
        MongoClient,
        RawBatchCursor,
        RawBatchCommandCursor,
    ]

    def __init__(
        self,
        dispatch: Union[
            "_LatentCursor",
            ClientSession,
            Collection,
            CommandCursor,
            Cursor,
            Database,
            MongoClient,
            RawBatchCursor,
            RawBatchCommandCursor,
        ],
    ) -> None:
        self.dispatch = dispatch

    def __eq__(self, other: Any) -> bool:
        if (
            isinstance(other, self.__class__)
            and hasattr(self, "dispatch")
            and hasattr(self, "dispatch")
        ):
            return self.dispatch == other.dispatch

        return NotImplemented

    def __repr__(self) -> str:
        return type(self).__name__ + f"({self.dispatch!r})"


class AsyncBaseProperty(AsyncBase):
    """Base class property for AsyncIOMongoDB instances"""

    dispatch: Union[Collection, Database, MongoClient]

    @property
    def codec_options(self) -> CodecOptions:
        return self.dispatch.codec_options

    @property
    def read_preference(self) -> _ServerMode:
        return self.dispatch.read_preference

    @property
    def read_concern(self) -> ReadConcern:
        return self.dispatch.read_concern

    @property
    def write_concern(self) -> WriteConcern:
        return self.dispatch.write_concern
