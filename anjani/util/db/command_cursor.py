"""Anjani database commmand cursor"""
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

import asyncio
from collections import deque
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Coroutine,
    Deque,
    Generic,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from pymongo.client_session import ClientSession
from pymongo.command_cursor import CommandCursor as _CommandCursor
from pymongo.typings import _Address, _DocumentType

from anjani import util

from .client_session import AsyncClientSession
from .cursor_base import AsyncCursorBase

if TYPE_CHECKING:
    from .collection import AsyncCollection


class CommandCursor(_CommandCursor, Generic[_DocumentType]):

    _CommandCursor__data: Deque[Any]
    _CommandCursor__killed: bool

    delegate: "AsyncCollection"

    def __init__(
        self,
        collection: "AsyncCollection",
        cursor_info: Mapping[str, Any],
        address: Optional[Union[Tuple[str, int], _Address]] = None,
        *,
        batch_size: int = 0,
        max_await_time_ms: Optional[int] = None,
        session: Optional[AsyncClientSession] = None,
        explicit_session: bool = False,
    ) -> None:
        self.delegate = collection

        super().__init__(
            collection.dispatch,
            cursor_info,
            address,
            batch_size=batch_size,
            max_await_time_ms=max_await_time_ms,
            session=session.dispatch if session else session,
            explicit_session=explicit_session,
        )

    async def _AsyncCommandCursor__die(self, synchronous: bool = False) -> None:
        await util.run_sync(self.__die, synchronous=synchronous)

    @property
    def _AsyncCommandCursor__data(self) -> Deque[Any]:
        return self.__data

    @property
    def _AsyncCommandCursor__killed(self) -> bool:
        return self.__killed

    @property
    def collection(self) -> "AsyncCollection[_DocumentType]":
        return self.delegate


class RawBatchCommandCursor(CommandCursor, Generic[_DocumentType]):
    pass


class AsyncCommandCursor(AsyncCursorBase):
    """AsyncIO :obj:`~CommandCursor`

    *DEPRECATED* methods are removed in this class.
    """

    dispatch: CommandCursor

    def _query_flags(self) -> int:
        return 0

    def _data(self) -> Deque[Any]:
        return self.dispatch._CommandCursor__data  # skipcq: PYL-W0212

    def _killed(self) -> bool:
        return self.dispatch._CommandCursor__killed  # skipcq: PYL-W0212


class _LatentCursor(Generic[_DocumentType]):
    """Base class for LatentCursor AsyncIOMongoDB instance"""

    # ClassVar
    alive: ClassVar[bool] = True
    _CommandCursor__data: ClassVar[Deque[Any]] = deque()
    _CommandCursor__id: ClassVar[Optional[Any]] = None
    _CommandCursor__killed: ClassVar[bool] = False
    _CommandCursor__sock_mgr: ClassVar[Optional[Any]] = None
    _CommandCursor__session: ClassVar[Optional[AsyncClientSession]] = None
    _CommandCursor__explicit_session: ClassVar[Optional[bool]] = None
    address: ClassVar[Optional[Union[Tuple[str, int], _Address]]] = None
    cursor_id: ClassVar[Optional[Any]] = None
    session: Optional[ClientSession] = None

    _CommandCursor__collection: "AsyncCollection"

    def __init__(self, collection: "AsyncCollection") -> None:
        self._CommandCursor__collection = collection

    def _CommandCursor__end_session(self, *args: Any, **kwargs: Any) -> None:
        pass  # Only for initialization

    def _CommandCursor__die(self, *args: Any, **kwargs: Any) -> None:
        pass  # Only for initialization

    def _refresh(self) -> int:  # skipcq: PYL-R0201
        """Only for initialization"""
        return 0

    def batch_size(self, batch_size: int) -> None:
        pass  # Only for initialization

    def close(self) -> None:
        pass  # Only for initialization

    def clone(self) -> "_LatentCursor":
        return _LatentCursor(self._CommandCursor__collection)

    def rewind(self):
        pass  # Only for initialization

    @property
    def collection(self):
        return self._CommandCursor__collection


class AsyncLatentCommandCursor(AsyncCommandCursor):
    """Temporary Cursor for initializing in aggregate,
    and will be overwrite by :obj:`~asyncio.Future`"""

    dispatch: Union[CommandCursor, RawBatchCommandCursor]

    def __init__(
        self,
        collection: "AsyncCollection",
        start: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.start = start
        self.args = args
        self.kwargs = kwargs

        super().__init__(_LatentCursor(collection), collection)

    def batch_size(self, batch_size: int) -> "AsyncLatentCommandCursor":
        self.kwargs["batchSize"] = batch_size

        return self

    def _get_more(self) -> Union[asyncio.Future[int], Coroutine[Any, Any, int]]:
        if not self.started:
            self.started = True
            original_future = self.loop.create_future()
            future = self.loop.create_task(util.run_sync(self.start, *self.args, **self.kwargs))
            future.add_done_callback(
                partial(self.loop.call_soon_threadsafe, self._on_started, original_future)
            )

            self.start, self.args, self.kwargs = lambda _: None, (), {}

            return original_future

        return super()._get_more()

    def _on_started(
        self,
        original_future: asyncio.Future[int],
        future: asyncio.Future[Union[CommandCursor, RawBatchCommandCursor]],
    ) -> None:
        try:
            self.dispatch = future.result()
        except Exception as exc:  # skipcq: PYL-W0703
            if not original_future.done():
                original_future.set_exception(exc)
        else:
            # Return early if the task was cancelled.
            if original_future.done():
                return

            if self.dispatch._CommandCursor__data or not self.dispatch.alive:  # skipcq: PYL-W0212
                # _get_more is complete.
                original_future.set_result(
                    len(self.dispatch._CommandCursor__data)  # skipcq: PYL-W0212
                )
            else:
                # Send a getMore.
                fut = self.loop.create_task(super()._get_more())

                def copy(f: asyncio.Future[int]) -> None:
                    if original_future.done():
                        return

                    exc = f.exception()
                    if exc is not None:
                        original_future.set_exception(exc)
                    else:
                        original_future.set_result(f.result())

                fut.add_done_callback(copy)
