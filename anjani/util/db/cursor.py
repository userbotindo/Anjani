"""Anjani database cursor"""
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

from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Deque,
    Generic,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from bson.code import Code
from pymongo.cursor import Cursor as _Cursor
from pymongo.typings import _CollationIn, _DocumentType

from anjani import util

from .cursor_base import AsyncCursorBase

if TYPE_CHECKING:
    from .collection import AsyncCollection


class Cursor(_Cursor, Generic[_DocumentType]):

    _Cursor__data: Deque[Any]
    _Cursor__killed: bool
    _Cursor__query_flags: int

    delegate: "AsyncCollection[_DocumentType]"

    def __init__(
        self, collection: "AsyncCollection[_DocumentType]", *args: Any, **kwargs: Any
    ) -> None:
        self.delegate = collection

        super().__init__(collection.dispatch, *args, **kwargs)

    @abstractmethod
    def add_option(self, mask: int) -> "Cursor[_DocumentType]":
        raise NotImplementedError

    @abstractmethod
    def allow_disk_use(self, allow_disk_use: bool) -> "Cursor[_DocumentType]":
        raise NotImplementedError

    @abstractmethod
    def collation(self, collation: Optional[_CollationIn]) -> "Cursor[_DocumentType]":
        raise NotImplementedError

    @abstractmethod
    def comment(self, comment: str) -> "Cursor[_DocumentType]":
        raise NotImplementedError

    @property
    def _AsyncCursor__data(self) -> Deque[Any]:
        return self.__data

    async def _AsyncCursor__die(self, synchronous: bool = False) -> None:
        await util.run_sync(self.__die, synchronous=synchronous)

    @property
    def _AsyncCursor__exhaust(self) -> bool:
        return self.__exhaust

    @property
    def _AsyncCursor__killed(self) -> bool:
        return self.__killed

    @property
    def _AsyncCursor__max_await_time_ms(self) -> Optional[int]:
        return self.__max_await_time_ms

    @property
    def _AsyncCursor__max_time_ms(self) -> Optional[int]:
        return self.__max_time_ms

    @property
    def _AsyncCursor__query_flags(self) -> int:
        return self.__query_flags

    @property
    def _AsyncCursor__query_spec(self) -> Optional[Any]:
        return self.__query_spec

    @property
    def _AsyncCursor__retrieved(self) -> int:
        return self.__retrieved

    @property
    def _AsyncCursor__spec(self) -> Mapping[str, Any]:
        return self.__spec

    @property
    def collection(self) -> "AsyncCollection[_DocumentType]":
        return self.delegate


class RawBatchCursor(Cursor):  # skipcq: PYL-W0223
    pass


class AsyncCursor(AsyncCursorBase, Generic[_DocumentType]):
    """AsyncIO :obj:`~Cursor`

    *DEPRECATED* methods are removed in this class.
    """

    dispatch: _Cursor

    def add_option(self, mask: int) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.add_option(mask)
        return self

    def allow_disk_use(self, allow_disk_use: bool) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.allow_disk_use(allow_disk_use)
        return self

    def collation(self, collation: _CollationIn) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.collation(collation)
        return self

    def comment(self, comment: str) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.comment(comment)
        return self

    async def distinct(self, key: str) -> List[Any]:
        return await util.run_sync(self.dispatch.distinct, key)

    async def explain(self) -> _DocumentType:
        return await util.run_sync(self.dispatch.explain)

    def hint(self, index: Union[str, List[Tuple[str, Any]]]) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.hint(index)
        return self

    def limit(self, limit: int) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.limit(limit)
        return self

    def max(self, spec: List[Any]) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.max(spec)
        return self

    def max_await_time_ms(self, max_await_time_ms: int) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.max_await_time_ms(max_await_time_ms)
        return self

    def max_time_ms(self, max_time_ms: int) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.max_time_ms(max_time_ms)
        return self

    def min(self, spec: List[Any]) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.min(spec)
        return self

    def remove_option(self, mask: int) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.remove_option(mask)
        return self

    def rewind(self) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.rewind()
        return self

    def skip(self, skip: int) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.skip(skip)
        return self

    def sort(
        self, key: Union[str, List[Tuple[str, Any]]], *, direction: Any = None
    ) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.sort(key, direction=direction)
        return self

    def where(self, code: Code) -> "AsyncCursor[_DocumentType]":
        self.dispatch = self.dispatch.where(code)
        return self

    def _query_flags(self) -> int:
        # skipcq: PYL-W0212
        return self.dispatch._Cursor__query_flags  # type: ignore

    def _data(self) -> Deque[Any]:
        # skipcq: PYL-W0212
        return self.dispatch._Cursor__data  # type: ignore

    def _killed(self) -> bool:
        # skipcq: PYL-W0212
        return self.dispatch._Cursor__killed  # type: ignore


class AsyncRawBatchCursor(AsyncCursor, Generic[_DocumentType]):
    pass
