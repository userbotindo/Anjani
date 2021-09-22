
from typing import TYPE_CHECKING, Any, List, MutableMapping, Optional, Union

from bson.timestamp import Timestamp
from pymongo.change_stream import ChangeStream
from pymongo.collation import Collation

from .base import AsyncBase
from .client_session import AsyncClientSession

from anjani import util

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
        pipeline: Optional[List[MutableMapping[str, Any]]],
        full_document: Optional[str],
        resume_after: Optional[Any],
        max_await_time_ms: Optional[int],
        batch_size: Optional[int],
        collation: Optional[Collation],
        start_at_operation_time: Optional[Timestamp],
        session: Optional[AsyncClientSession],
        start_after: Optional[Any]
    ) -> None:
        self._target = target
        self._options: MutableMapping[str, Any] = {
            "pipeline": pipeline,
            "full_document": full_document,
            "resume_after": resume_after,
            "max_await_time_ms": max_await_time_ms,
            "batch_size": batch_size,
            "collation": collation,
            "start_at_operation_time": start_at_operation_time,
            "session": session.dispatch if session else session,
            "start_after": start_after
        }

        super().__init__(None)  # type: ignore

    def __aiter__(self) -> "AsyncChangeStream":
        return self

    def __iter__(self) -> None:
        raise RuntimeError("Use 'async for' instead of 'for'")

    async def __anext__(self) -> MutableMapping[str, Any]:
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
            self.dispatch = await util.run_sync(
                self._target.dispatch.watch, **self._options)

        return self.dispatch

    async def _try_next(self) -> Optional[MutableMapping[str, Any]]:
        self.dispatch = await self._init()
        return await util.run_sync(self.dispatch.try_next)

    async def close(self):
        if self.dispatch:
            await util.run_sync(self.dispatch.close)

    async def next(self) -> MutableMapping[str, Any]:
        while self.alive:
            document = await self.try_next()
            if document:
                return document

        raise StopAsyncIteration

    async def try_next(self) -> Optional[MutableMapping[str, Any]]:
        return await self._try_next()

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
