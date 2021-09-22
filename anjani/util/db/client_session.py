from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Coroutine, MutableMapping, Optional

from pymongo.client_session import ClientSession, SessionOptions
from pymongo.monotonic import time as monotonic_time
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from .base import AsyncBase
from .errors import OperationFailure, PyMongoError
from .types import ReadPreferences, Results

from anjani import util

if TYPE_CHECKING:
    from .client import AsyncClient


class AsyncClientSession(AsyncBase):
    """AsyncIO :obj:`~ClientSession`

       *DEPRECATED* methods are removed in this class.
    """

    _client: "AsyncClient"

    dispatch: ClientSession

    def __init__(self, client: "AsyncClient", dispatch: ClientSession) -> None:
        self._client = client

        # Propagate initialization to base
        super().__init__(dispatch)

    async def __aenter__(self) -> "AsyncClientSession":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await util.run_sync(self.dispatch.__exit__, exc_type, exc_val, exc_tb)

    def __enter__(self) -> None:
        raise RuntimeError("Use 'async with' not just 'with'")

    async def abort_transaction(self) -> None:
        return await util.run_sync(self.dispatch.abort_transaction)

    async def commit_transaction(self) -> None:
        return await util.run_sync(self.dispatch.commit_transaction)

    async def end_session(self) -> None:
        return await util.run_sync(self.dispatch.end_session)

    @asynccontextmanager
    async def start_transaction(
        self,
        *,
        read_concern: Optional[ReadConcern] = None,
        write_concern: Optional[WriteConcern] = None,
        read_preference: Optional[ReadPreferences] = None,
        max_commit_time_ms: Optional[int] = None
    ) -> AsyncGenerator["AsyncClientSession", None]:
        await util.run_sync(
            self.dispatch.start_transaction,
            read_concern=read_concern,
            write_concern=write_concern,
            read_preference=read_preference,
            max_commit_time_ms=max_commit_time_ms
        )
        try:
            yield self
        except Exception:  # skipcq: PYL-W0703
            if self.in_transaction:
                await self.abort_transaction()
        else:
            if self.in_transaction:
                await self.commit_transaction()

    async def with_transaction(
        self,
        callback: Callable[["AsyncClientSession"], Coroutine[Any, Any, Results]],
        *,
        read_concern: Optional[ReadConcern] = None,
        write_concern: Optional[WriteConcern] = None,
        read_preference: Optional[ReadPreferences] = None,
        max_commit_time_ms: Optional[int] = None
    ) -> Results:
        # 99% Of this code from motor's lib

        def _within_time_limit(s: float) -> bool:
            return monotonic_time.time() - s < 120

        def _max_time_expired_error(exc: PyMongoError) -> bool:
            return isinstance(exc, OperationFailure) and exc.code == 50

        start_time = monotonic_time.time()
        while True:
            async with self.start_transaction(
                read_concern=read_concern,
                write_concern=write_concern,
                read_preference=read_preference,
                max_commit_time_ms=max_commit_time_ms
            ):
                try:
                    ret = await callback(self)
                except Exception as exc:
                    if self.in_transaction:
                        await self.abort_transaction()
                    if (isinstance(exc, PyMongoError) and
                            exc.has_error_label("TransientTransactionError")
                            and _within_time_limit(start_time)):
                        # Retry the entire transaction.
                        continue
                    raise

            if not self.in_transaction:
                # Assume callback intentionally ended the transaction.
                return ret

            while True:
                try:
                    await self.commit_transaction()
                except PyMongoError as exc:
                    if (exc.has_error_label("UnknownTransactionCommitResult")
                            and _within_time_limit(start_time)
                            and not _max_time_expired_error(exc)):
                        # Retry the commit.
                        continue

                    if (exc.has_error_label("TransientTransactionError") and
                            _within_time_limit(start_time)):
                        # Retry the entire transaction.
                        break
                    raise

                # Commit succeeded.
                return ret

    def advance_cluster_time(self, cluster_time: int) -> None:
        self.dispatch.advance_cluster_time(cluster_time=cluster_time)

    def advance_operation_time(self, operation_time: int) -> None:
        self.dispatch.advance_operation_time(operation_time=operation_time)

    @property
    def client(self) -> "AsyncClient":
        return self._client

    @property
    def cluster_time(self) -> Optional[int]:
        return self.dispatch.cluster_time

    @property
    def has_ended(self) -> bool:
        return self.dispatch.has_ended

    @property
    def in_transaction(self) -> bool:
        return self.dispatch.in_transaction

    @property
    def operation_time(self) -> Optional[int]:
        return self.dispatch.operation_time

    @property
    def options(self) -> SessionOptions:
        return self.dispatch.options

    @property
    def session_id(self) -> MutableMapping[str, Any]:
        return self.dispatch.session_id
