"""Anjani database cursor core"""
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

import asyncio
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Coroutine,
    Deque,
    List,
    MutableMapping,
    Optional,
    Tuple,
    Union,
)

from pymongo.cursor import _QUERY_OPTIONS, Cursor, RawBatchCursor

from anjani import util

from .base import AsyncBase
from .client_session import AsyncClientSession
from .errors import InvalidOperation

if TYPE_CHECKING:
    from .collection import AsyncCollection
    from .command_cursor import CommandCursor, _LatentCursor


class AsyncCursorBase(AsyncBase):
    """Base class for Cursor AsyncIOMongoDB instances

    *DEPRECATED* methods are removed in this class.

    :meth:`~each()` is removed because we can iterate directly this class,
    And we now have :meth:`~to_list()` so yeah kinda useless
    """

    collection: "AsyncCollection"
    dispatch: Union["_LatentCursor", "CommandCursor", Cursor, RawBatchCursor]
    loop: asyncio.AbstractEventLoop

    def __init__(
        self,
        cursor: Union["_LatentCursor", "CommandCursor", Cursor, RawBatchCursor],
        collection: "AsyncCollection" = None,
    ) -> None:
        super().__init__(cursor)

        if collection:
            self.collection = collection
        else:
            self.collection = cursor.collection
        self.started = False
        self.closed = False

        self.loop = asyncio.get_event_loop()

    def __aiter__(self) -> "AsyncCursorBase":
        return self

    async def __anext__(self) -> MutableMapping[str, Any]:
        return await self.next()

    def _buffer_size(self) -> int:
        return len(self._data())

    def _query_flags(self) -> int:
        raise NotImplementedError

    def _data(self) -> Deque[Any]:
        raise NotImplementedError

    def _killed(self) -> bool:
        raise NotImplementedError

    def _get_more(self) -> Union[asyncio.Future[int], Coroutine[Any, Any, int]]:
        if not self.alive:
            raise InvalidOperation(
                "Can't call get_more() on a AsyncCursor that has been" " exhausted or killed."
            )

        self.started = True
        return self._refresh()

    def _to_list(
        self,
        length: Optional[int],
        the_list: List[MutableMapping[str, Any]],
        future: asyncio.Future[List[MutableMapping[str, Any]]],
        get_more_future: asyncio.Future[int],
    ) -> None:
        # get_more_future is the result of self._get_more().
        # future will be the result of the user's to_list() call.
        try:
            result = get_more_future.result()
            # Return early if the task was cancelled.
            if future.done():
                return
            collection = self.collection
            fix_outgoing = collection.database._fix_outgoing  # skipcq: PYL-W0212

            if length is None:
                n = result
            else:
                n = min(length - len(the_list), result)

            i = 0
            while i < n:
                the_list.append(fix_outgoing(self._data().popleft(), collection))
                i += 1

            reached_length = length is not None and len(the_list) >= length
            if reached_length or not self.alive:
                future.set_result(the_list)
            else:
                new_future = self.loop.create_task(self._get_more())
                new_future.add_done_callback(
                    partial(self.loop.call_soon_threadsafe, self._to_list, length, the_list, future)
                )
        except Exception as exc:  # skipcq: PYL-W0703
            if not future.done():
                future.set_exception(exc)

    async def _refresh(self) -> int:
        return await util.run_sync(self.dispatch._refresh)  # skipcq: PYL-W0212

    def batch_size(self, batch_size: int) -> "AsyncCursorBase":
        self.dispatch.batch_size(batch_size)
        return self

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            await util.run_sync(self.dispatch.close)

    async def next(self) -> Any:
        if self.alive and (self._buffer_size() or await self._get_more()):
            return await util.run_sync(next, self.dispatch)
        raise StopAsyncIteration

    def to_list(
        self, length: Optional[int] = None
    ) -> asyncio.Future[List[MutableMapping[str, Any]]]:
        if length is not None and length < 0:
            raise ValueError("length must be non-negative")

        if self._query_flags() & _QUERY_OPTIONS["tailable_cursor"]:
            raise InvalidOperation("Can't call to_list on tailable cursor")

        future = self.loop.create_future()
        the_list: List[MutableMapping[str, Any]] = []

        if not self.alive:
            future.set_result(the_list)
            return future

        get_more_future = self.loop.create_task(self._get_more())
        get_more_future.add_done_callback(
            partial(self.loop.call_soon_threadsafe, self._to_list, length, the_list, future)
        )

        return future

    @property
    def address(self) -> Optional[Tuple[str, int]]:
        return self.dispatch.address

    @property
    def alive(self) -> bool:
        if not self.dispatch:
            return True
        return self.dispatch.alive

    @property
    def cursor_id(self) -> Optional[int]:
        return self.dispatch.cursor_id

    @property
    def session(self) -> Optional[AsyncClientSession]:
        return self.dispatch.session
