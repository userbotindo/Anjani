"""Anjani database stream"""
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

from typing import TYPE_CHECKING, Any, List, Literal, Mapping, Optional, Union

from bson.timestamp import Timestamp
from pymongo.change_stream import ChangeStream
from pymongo.collation import Collation

from anjani import util

from .base import AsyncBase
from .client_session import AsyncClientSession

if TYPE_CHECKING:
    from .client import AsyncClient
    from .collection import AsyncCollection
    from .db import AsyncDatabase


class AsyncChangeStream(AsyncBase):
    """AsyncIO :obj:`~ChangeStream`

    *DEPRECATED* methods are removed in this class.
    """

    _target: Union["AsyncClient", "AsyncDatabase", "AsyncCollection"]

    dispatch: ChangeStream

    def __init__(
        self,
        target: Union["AsyncClient", "AsyncDatabase", "AsyncCollection"],
        pipeline: Optional[List[Mapping[str, Any]]],
        full_document: Optional[Literal["updateLookup"]],
        resume_after: Optional[Mapping[str, str]],
        max_await_time_ms: Optional[int],
        batch_size: Optional[int],
        collation: Optional[Collation],
        start_at_operation_time: Optional[Timestamp],
        session: Optional[AsyncClientSession],
        start_after: Optional[Mapping[str, str]],
        comment: Optional[str],
        full_document_before_change: Optional[Literal["required", "whenAvailable"]] = None,
    ) -> None:
        self._target = target
        self._options: Mapping[str, Any] = {
            "pipeline": pipeline,
            "full_document": full_document,
            "resume_after": resume_after,
            "max_await_time_ms": max_await_time_ms,
            "batch_size": batch_size,
            "collation": collation,
            "start_at_operation_time": start_at_operation_time,
            "session": session.dispatch if session else session,
            "start_after": start_after,
            "comment": comment,
            "full_document_before_change": full_document_before_change,
        }

        super().__init__(None)  # type: ignore

    def __aiter__(self) -> "AsyncChangeStream":
        return self

    def __iter__(self) -> None:
        raise RuntimeError("Use 'async for' instead of 'for'")

    async def __anext__(self) -> Mapping[str, Any]:
        return await self.next()

    async def __aenter__(self) -> "AsyncChangeStream":
        if not self.dispatch:
            await self._init()

        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.dispatch:
            await self.close()

    def __enter__(self) -> None:
        raise RuntimeError("Use 'async with' not just 'with'")

    async def _init(self) -> ChangeStream:
        if not self.dispatch:
            self.dispatch = await util.run_sync(self._target.dispatch.watch, **self._options)

        return self.dispatch

    async def close(self):
        if self.dispatch:
            await util.run_sync(self.dispatch.close)

    async def next(self) -> Mapping[str, Any]:
        while self.alive:
            document = await self.try_next()
            if document:
                return document

        raise StopAsyncIteration

    async def try_next(self) -> Optional[Mapping[str, Any]]:
        self.dispatch = await self._init()
        return await util.run_sync(self.dispatch.try_next)

    @property
    def alive(self) -> bool:
        if not self.dispatch:
            return True

        return self.dispatch.alive

    @property
    def resume_token(self) -> Any:
        if self.dispatch:
            return self.dispatch.resume_token

        return None
