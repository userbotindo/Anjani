import asyncio
from collections import deque
from contextlib import asynccontextmanager
from functools import partial
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Callable,
    ClassVar,
    Coroutine,
    Deque,
    FrozenSet,
    List,
    MutableMapping,
    Optional, 
    Set,
    Tuple,
    TypeVar,
    Union
)

from bson import CodecOptions, DBRef
from bson.code import Code
from bson.codec_options import DEFAULT_CODEC_OPTIONS
from bson.timestamp import Timestamp
from bson.son import SON
from pymongo import (
    DeleteOne,
    IndexModel,
    InsertOne,
    MongoClient,
    ReplaceOne
)
from pymongo.change_stream import ChangeStream
from pymongo.client_session import ClientSession, SessionOptions
from pymongo.collation import Collation
from pymongo.collection import Collection
from pymongo.command_cursor import CommandCursor as _CommandCursor, RawBatchCommandCursor
from pymongo.cursor import Cursor as _Cursor, RawBatchCursor, _QUERY_OPTIONS
from pymongo.database import Database
from pymongo.driver_info import DriverInfo
from pymongo.errors import InvalidOperation, OperationFailure, PyMongoError
from pymongo.monotonic import time as monotonic_time
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import (
    _ServerMode,
    Primary,
    PrimaryPreferred,
    ReadPreference,
    Secondary,
    SecondaryPreferred,
    Nearest
)
from pymongo.results import (
    BulkWriteResult,
    DeleteResult,
    InsertManyResult,
    InsertOneResult,
    UpdateResult
)
from pymongo.topology_description import TopologyDescription
from pymongo.write_concern import DEFAULT_WRITE_CONCERN, WriteConcern

from anjani import util

PREFERENCE = Union[Primary, PrimaryPreferred, Secondary, SecondaryPreferred, Nearest]
JavaScriptCode = TypeVar("JavaScriptCode", bound=str)
Requests = Union[DeleteOne, InsertOne, ReplaceOne]
Results = TypeVar("Results")


class Cursor(_Cursor):

    _Cursor__data: Deque[Any]
    _Cursor__killed: bool
    _Cursor__query_flags: int

    def __init__(self, collection: Collection, *args: Any, **kwargs: Any) -> None:
        super().__init__(collection, *args, **kwargs)

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
    def _AsyncCursor__spec(self) -> MutableMapping[str, Any]:
        return self.__spec

    @property
    def collection(self) -> "AsyncCollection":
        return self.__collection


class CommandCursor(_CommandCursor):

    _CommandCursor__data: Deque[Any]
    _CommandCursor__killed: bool

    def __init__(
        self,
        collection: "AsyncCollection",
        cursor_info: MutableMapping[str, Any],
        address: Optional[Tuple[str, int]] = None,
        *,
        batch_size: int = 0,
        max_await_time_ms: Optional[int] = None,
        session: Optional["AsyncClientSession"] = None,
        explicit_session: bool = False,
    ) -> None:
        super().__init__(
            collection,
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
    def collection(self) -> "AsyncCollection":
        return self.__collection


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
        RawBatchCommandCursor
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
            RawBatchCommandCursor
        ]
    ) -> None:
        self.dispatch = dispatch

    def __eq__(self, other: Any) -> bool:
        if (isinstance(other, self.__class__) and
                hasattr(self, "dispatch") and
                hasattr(self, "dispatch")):
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

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

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
        read_preference: Optional[PREFERENCE] = None,
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
        except Exception:
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
        read_preference: Optional[PREFERENCE] = None,
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


class AsyncClient(AsyncBaseProperty):
    """AsyncIO :obj:`~MongoClient`

       *DEPRECATED* methods are removed in this class.
    """

    dispatch: MongoClient

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.update({"driver":
                       DriverInfo(
                           name="AsyncIOMongoDB",
                           version="staging",
                           platform="AsyncIO"
                        )})
        dispatch = MongoClient(*args, **kwargs)

        # Propagate initialization to base
        super().__init__(dispatch)

    def __getitem__(self, name: str) -> "AsyncDB":
        return AsyncDB(self, self.dispatch[name])

    async def close(self) -> None:
        await util.run_sync(self.dispatch.close)

    async def drop_database(
        self,
        name_or_database: Union[str, "AsyncDB"],
        session: Optional[AsyncClientSession] = None
    ) -> None:
        if isinstance(name_or_database, AsyncDB):
            name_or_database = name_or_database.name

        return await util.run_sync(
            self.dispatch.drop_database,
            name_or_database,
            session=session.dispatch if session else session
        )

    def get_database(
        self,
        name: Optional[str] = None,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[PREFERENCE] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None
    ) -> "AsyncDB":
        return AsyncDB(
            self,
            self.dispatch.get_database(
                name,
                codec_options=codec_options,
                read_preference=read_preference,
                write_concern=write_concern,
                read_concern=read_concern
            )
        )

    def get_default_database(
        self,
        default: Optional[str] = None,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[PREFERENCE] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None
    ) -> "AsyncDB":
        return AsyncDB(
            self,
            self.dispatch.get_default_database(
                default,
                codec_options=codec_options,
                read_preference=read_preference,
                write_concern=write_concern,
                read_concern=read_concern
            )
        )

    async def list_database_names(
        self, session: Optional[AsyncClientSession] = None) -> List[str]:
        return await util.run_sync(self.dispatch.list_database_names,
                                   session=session.dispatch if session else session)

    async def list_databases(
        self, session: Optional[AsyncClientSession] = None, **kwargs: Any
    ) -> "AsyncCommandCursor":
        cmd = SON([("listDatabases", 1)])
        cmd.update(kwargs)
        database = self.get_database("admin",
                                     codec_options=DEFAULT_CODEC_OPTIONS,
                                     read_preference=ReadPreference.PRIMARY,
                                     write_concern=DEFAULT_WRITE_CONCERN)
        res: MutableMapping[str, Any] = await util.run_sync(
            database.dispatch._retryable_read_command,
            cmd,
            session=session.dispatch if session else session
        )
        cursor: MutableMapping[str, Any] = {
            "id": 0,
            "firstBatch": res["databases"],
            "ns": "admin.$cmd",
        }
        return AsyncCommandCursor(CommandCursor(database["$cmd"], cursor, None))

    async def server_info(
        self, session: Optional[AsyncClientSession] = None
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.server_info,
            session=session.dispatch if session else session
        )

    # Don't need await when entering the context manager,
    # because it's slightly different than motor libs.
    @asynccontextmanager
    async def start_session(
        self,
        *,
        causal_consistency: Any = None,
        default_transaction_options: Any = None,
        snapshot: bool = False,
    ) -> AsyncGenerator[AsyncClientSession, None]:
        session = await util.run_sync(
            self.dispatch.start_session,
            causal_consistency=causal_consistency,
            default_transaction_options=default_transaction_options,
            snapshot=snapshot
        )

        async with AsyncClientSession(self, session) as session:
            yield session

    def watch(
        self,
        pipeline: Optional[List[MutableMapping[str, Any]]] = None,
        *,
        full_document: Optional[str] = None,
        resume_after: Optional[Any] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[Collation] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[AsyncClientSession] = None,
        start_after: Optional[Any] = None
    ) -> "AsyncChangeStream":
        return AsyncChangeStream(
            self,
            pipeline,
            full_document,
            resume_after,
            max_await_time_ms,
            batch_size,
            collation,
            start_at_operation_time,
            session,
            start_after
        )

    @property
    def HOST(self) -> str:
        return self.dispatch.HOST

    @property
    def PORT(self) -> int:
        return self.dispatch.PORT

    @property
    def address(self) -> Optional[Tuple[str, int]]:
        return self.dispatch.address

    @property
    def arbiters(self) -> Set[Tuple[str, int]]:
        return self.dispatch.arbiters

    @property
    def event_listeners(self) -> Any:
        return self.dispatch.event_listeners

    @property
    def is_mongos(self) -> bool:
        return self.dispatch.is_mongos

    @property
    def is_primary(self) -> bool:
        return self.dispatch.is_primary

    @property
    def local_threshold_ms(self) -> int:
        return self.dispatch.local_threshold_ms

    @property
    def max_bson_size(self) -> int:
        return self.dispatch.max_bson_size

    @property
    def max_idle_time_ms(self) -> Optional[int]:
        return self.dispatch.max_idle_time_ms

    @property
    def max_message_size(self) -> int:
        return self.dispatch.max_message_size

    @property
    def max_pool_size(self) -> int:
        return self.dispatch.max_pool_size

    @property
    def max_write_batch_size(self) -> int:
        return self.dispatch.max_write_batch_size

    @property
    def min_pool_size(self) -> int:
        return self.dispatch.min_pool_size

    @property
    def nodes(self) -> FrozenSet[Set[Tuple[str, int]]]:
        return self.dispatch.nodes

    @property
    def primary(self) -> Optional[Tuple[str, int]]:
        return self.dispatch.primary

    @property
    def retry_reads(self) -> bool:
        return self.dispatch.retry_reads

    @property
    def retry_writes(self) -> bool:
        return self.dispatch.retry_writes

    @property
    def secondaries(self) -> Set[Tuple[str, int]]:
        return self.dispatch.secondaries

    @property
    def server_selection_timeout(self) -> int:
        return self.dispatch.server_selection_timeout

    @property
    def topology_description(self) -> TopologyDescription:
        return self.dispatch.topology_description


class AsyncDB(AsyncBaseProperty):
    """AsyncIO :obj:`~Database`

       *DEPRECATED* methods are removed in this class.
    """

    _client: AsyncClient

    dispatch: Database

    def __init__(self, client: AsyncClient, database: Database) -> None:
        self._client = client

        # Propagate initialization to base
        super().__init__(database)

    def __getitem__(self, name) -> "AsyncCollection":
        return AsyncCollection(Collection(self.dispatch, name))

    def aggregate(
        self,
        pipeline: List[MutableMapping[str, Any]],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> "AsyncLatentCommandCursor":
        return AsyncLatentCommandCursor(
            self["$cmd.aggregate"],
            self.dispatch.aggregate,
            pipeline,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def command(
        self,
        command: Union[str, MutableMapping[str, Any]],
        *,
        value: int = 1,
        check: bool = True,
        allowable_errors: Optional[str] = None,
        read_preference: Optional[PREFERENCE] = None,
        codec_options: Optional[CodecOptions] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> MutableMapping[str, Any]:
        return await self.dispatch.command(
            command,
            value=value,
            check=check,
            allowable_errors=allowable_errors,
            read_preference=read_preference,
            codec_options=codec_options,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def close(self) -> None:
        await self._client.close()

    async def create_collection(
        self,
        name: str,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[PREFERENCE] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> "AsyncCollection":
        return AsyncCollection(
            await util.run_sync(
                self.dispatch.create_collection,
                name,
                codec_options=codec_options,
                read_preference=read_preference,
                write_concern=write_concern,
                read_concern=read_concern,
                session=session.dispatch if session else session,
                **kwargs
            )
        )

    async def dereference(
        self, dbref: DBRef, *, session: Optional[AsyncClientSession] = None, **kwargs: Any
    ) -> Optional[MutableMapping[str, Any]]:
        return await util.run_sync(
            self.dispatch.dereference,
            dbref,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def drop_collection(
        self,
        name_or_collection: Union[str, "AsyncCollection"],
        session: Optional[AsyncClientSession] = None
    ) -> MutableMapping[str, Any]:
        if isinstance(name_or_collection, AsyncCollection):
            name_or_collection = name_or_collection.name

        return await util.run_sync(
            self.dispatch.drop_collection,
            name_or_collection,
            session=session.dispatch if session else session
        )

    def get_collection(
        self,
        name: str,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[PREFERENCE] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None
    ) -> "AsyncCollection":
        return AsyncCollection(
            self.dispatch.get_collection(
                name,
                codec_options=codec_options,
                read_preference=read_preference,
                write_concern=write_concern,
                read_concern=read_concern
            )
        )

    async def list_collection_names(
        self,
        *,
        session: Optional[AsyncClientSession] = None,
        filter: Optional[MutableMapping[str, Any]] = None,
        **kwargs: Any
    ) -> List[str]:
        return await util.run_sync(
            self.dispatch.list_collection_names,
            session=session.dispatch if session else session,
            filter=filter,
            **kwargs
        )

    async def list_collections(
        self,
        *,
        session: Optional[AsyncClientSession] = None,
        filter: Optional[MutableMapping[str, Any]] = None,
        **kwargs: Any
    ) -> "AsyncCommandCursor":
        cmd = SON([("listCollections", 1)])
        cmd.update(filter, **kwargs)

        res: MutableMapping[str, Any] = await util.run_sync(
            self.dispatch._retryable_read_command,
            cmd,
            session=session.dispatch if session else session
        )
        return AsyncCommandCursor(CommandCursor(self["$cmd"], res["cursor"], None))

    async def validate_collection(
        self,
        name_or_collection: Union[str, "AsyncCollection"],
        *,
        scandata: bool = False,
        full: bool = False,
        session: Optional[AsyncClientSession] = None,
        background: Optional[bool] = None
    ) -> MutableMapping[str, Any]:
        if isinstance(name_or_collection, AsyncCollection):
            name_or_collection = name_or_collection.name

        return await util.run_sync(
            self.dispatch.validate_collection,
            name_or_collection,
            scandata=scandata,
            full=full,
            session=session.dispatch if session else session,
            background=background
        )

    def watch(
        self,
        pipeline: Optional[List[MutableMapping[str, Any]]] = None,
        *,
        full_document: Optional[str] = None,
        resume_after: Optional[Any] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[Collation] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[AsyncClientSession] = None,
        start_after: Optional[Any] = None
    ) -> "AsyncChangeStream":
        return AsyncChangeStream(
            self,
            pipeline,
            full_document,
            resume_after,
            max_await_time_ms,
            batch_size,
            collation,
            start_at_operation_time,
            session,
            start_after
        )

    def with_options(
        self,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[PREFERENCE] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None
    ) -> "AsyncDB":
        self.dispatch = self.dispatch.with_options(
            codec_options=codec_options,
            read_preference=read_preference,
            write_concern=write_concern,
            read_concern=read_concern
        )

        return self

    @property
    def client(self) -> AsyncClient:
        return self._client

    @property
    def name(self) -> str:
        return self.dispatch.name


class AsyncCollection(AsyncBaseProperty):
    """AsyncIO :obj:`~Collection`

       *DEPRECATED* methods are removed in this class.
    """

    dispatch: Collection

    def __init__(self, dispatch: Collection) -> None:
        # Propagate initialization to base
        super().__init__(dispatch)

    def __getitem__(self, name: str) -> "AsyncCollection":
        return AsyncCollection(
            Collection(
                self.database,
                f"{self.name}.{name}",
                False,
                self.codec_options,
                self.read_preference,
                self.write_concern,
                self.read_concern
            )
        )

    def aggregate(
        self,
        pipeline: List[MutableMapping[str, Any]],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> "AsyncLatentCommandCursor":
        return AsyncLatentCommandCursor(
            self,
            self.dispatch.aggregate,
            pipeline,
            session=session.dispatch if session else session,
            **kwargs
        )

    def aggregate_raw_batches(
        self,
        pipeline: List[MutableMapping[str, Any]],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> "AsyncLatentCommandCursor":
        return AsyncLatentCommandCursor(
            self,
            self.dispatch.aggregate_raw_batches,
            pipeline,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def bulk_write(
        self,
        request: List[Requests],
        *,
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: Optional[AsyncClientSession] = None
    ) -> BulkWriteResult:
        return await util.run_sync(
            self.dispatch.bulk_write,
            request,
            ordered=ordered,
            bypass_document_validation=bypass_document_validation,
            session=session.dispatch if session else session
        )

    async def count_documents(
        self,
        filter: MutableMapping[str, Any],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> int:
        return await util.run_sync(
            self.dispatch.count_documents,
            filter,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def create_index(
        self, keys: Union[str, List[Tuple[str, Any]]], **kwargs: Any
    ) -> str:
        return await util.run_sync(
            self.dispatch.create_index,
            keys,
            **kwargs
        )

    async def create_indexes(
        self,
        indexes: List[IndexModel],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> List[str]:
        return await util.run_sync(
            self.dispatch.create_indexes,
            indexes,
            session=session.dispatch if session else session,
            **kwargs
        ) 

    async def delete_many(
        self,
        filter: MutableMapping[str, Any],
        *,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None
    ) -> DeleteResult:
        return await util.run_sync(
            self.dispatch.delete_many,
            filter,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session
        )

    async def delete_one(
        self,
        filter: MutableMapping[str, Any],
        *,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None
    ) -> DeleteResult:
        return await util.run_sync(
            self.dispatch.delete_one,
            filter,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session
        )

    async def distinct(
        self,
        key: str,
        filter: Optional[MutableMapping[str, Any]] = None,
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> List[Any]:
        return await util.run_sync(
            self.dispatch.distinct,
            key,
            filter=filter,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def drop(self, session: Optional[AsyncClientSession] = None) -> None:
        await util.run_sync(
            self.dispatch.drop,
            session=session.dispatch if session else session
        )

    async def drop_index(
        self,
        index_or_name: Union[str, IndexModel],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> None:
        await util.run_sync(self.dispatch.drop_index,
                            index_or_name,
                            session=session.dispatch if session else session,
                            **kwargs)

    async def drop_indexes(self, session: Optional[AsyncClientSession] = None, **kwargs) -> None:
        await util.run_sync(
            self.dispatch.drop_indexes,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def estimated_document_count(self, **kwargs: Any) -> int:
        return await util.run_sync(self.dispatch.estimated_document_count, **kwargs)

    def find(self, *args: Any, **kwargs: Any) -> AsyncIterator[MutableMapping[str, Any]]:
        return AsyncCursor(Cursor(self.dispatch, *args, **kwargs), self)

    async def find_one(
        self,
        filter: Optional[MutableMapping[str, Any]] = None,
        *args: Any,
        **kwargs: Any
    ) -> Optional[MutableMapping[str, Any]]:
        return await util.run_sync(
            self.dispatch.find_one, filter, *args, **kwargs)

    async def find_one_and_delete(
        self,
        filter: MutableMapping[str, Any],
        *,
        projection: Optional[Union[List[Any], MutableMapping[str, Any]]] = None,
        sort: Optional[List[Tuple[str, Any]]] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.find_one_and_delete,
            filter,
            projection=projection,
            sort=sort,
            hint=hint,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def find_one_and_replace(
        self,
        filter: MutableMapping[str, Any],
        replacement: MutableMapping[str, Any],
        *,
        projection: Optional[Union[List[Any], MutableMapping[str, Any]]] = None,
        sort: Optional[List[Tuple[str, Any]]] = None,
        upsert: bool = False,
        return_document: bool = False,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.find_one_and_replace,
            filter,
            replacement,
            projection=projection,
            sort=sort,
            upsert=upsert,
            return_document=return_document,
            hint=hint,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def find_one_and_update(
        self,
        filter: MutableMapping[str, Any],
        update: MutableMapping[str, Any],
        *,
        projection: Optional[Union[List[Any], MutableMapping[str, Any]]] = None,
        sort: Optional[List[Tuple[str, Any]]] = None,
        upsert: bool = False,
        return_document: bool = False,
        array_filters: Optional[List[MutableMapping[str, Any]]] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.find_one_and_update,
            filter,
            update,
            projection=projection,
            sort=sort,
            upsert=upsert,
            return_document=return_document,
            array_filters=array_filters,
            hint=hint,
            session=session.dispatch if session else session,
            **kwargs
        )

    def find_raw_batches(self, *args: Any, **kwargs: Any) -> AsyncIterable["AsyncCommandCursor"]:
        if "session" in kwargs:
            session = kwargs["session"]
            kwargs["session"] = session.dispatch if session else session

        cursor = self.dispatch.find_raw_batches(*args, **kwargs)

        return AsyncRawBatchCursor(cursor, self)

    async def index_information(
        self, session: Optional[AsyncClientSession] = None
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.index_information,
            session=session.dispatch if session else session
        )

    async def inline_map_reduce(
        self,
        map: JavaScriptCode,
        reduce: JavaScriptCode,
        *,
        full_response: bool = False,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.inline_map_reduce,
            map,
            reduce,
            full_response=full_response,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def insert_many(
        self,
        documents: List[MutableMapping[str, Any]],
        *,
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: Optional[AsyncClientSession] = None
    ) -> InsertManyResult:
        return await util.run_sync(
            self.dispatch.insert_many,
            documents,
            ordered=ordered,
            bypass_document_validation=bypass_document_validation,
            session=session.dispatch if session else session
        )

    async def insert_one(
        self,
        document: MutableMapping[str, Any],
        *,
        bypass_document_validation: bool = False,
        session: Optional[AsyncClientSession] = None
    ) -> InsertOneResult:
        return await util.run_sync(
            self.dispatch.insert_one,
            document,
            bypass_document_validation=bypass_document_validation,
            session=session.dispatch if session else session
        )

    def list_indexes(
        self, session: Optional[AsyncClientSession] = None
    ) -> AsyncIterable[IndexModel]:
        return AsyncLatentCommandCursor(
            self,
            self.dispatch.list_indexes,
            session=session.dispatch if session else session
        )

    async def map_reduce(
        self,
        map: JavaScriptCode,
        reduce: JavaScriptCode,
        out: Union[str, MutableMapping[str, Any], SON],
        *,
        full_response: bool = False,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.map_reduce,
            map,
            reduce,
            out,
            full_response=full_response,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def options(
        self, session: Optional[AsyncClientSession] = None
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.options,
            session=session.dispatch if session else session
        )

    async def rename(
        self,
        new_name: str,
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.rename,
            new_name,
            session=session.dispatch if session else session,
            **kwargs
        )

    async def replace_one(
        self,
        filter: MutableMapping[str, Any],
        replacement: MutableMapping[str, Any],
        *,
        upsert: bool = False,
        bypass_document_validation: bool = False,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None
    ) -> UpdateResult:
        return await util.run_sync(
            self.dispatch.replace_one,
            filter,
            replacement,
            upsert=upsert,
            bypass_document_validation=bypass_document_validation,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session
        )

    async def update_many(
        self,
        filter: MutableMapping[str, Any],
        update: MutableMapping[str, Any],
        *,
        upsert: bool = False,
        array_filters: Optional[List[MutableMapping[str, Any]]] = None,
        bypass_document_validation: bool = False,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None
    ) -> UpdateResult:
        return await util.run_sync(
            self.dispatch.update_many,
            filter,
            update,
            upsert=upsert,
            array_filters=array_filters,
            bypass_document_validation=bypass_document_validation,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session
        )

    async def update_one(
        self,
        filter: MutableMapping[str, Any],
        update: MutableMapping[str, Any],
        *,
        upsert: bool = False,
        array_filters: Optional[List[MutableMapping[str, Any]]] = None,
        bypass_document_validation: bool = False,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None
    ) -> UpdateResult:
        return await util.run_sync(
            self.dispatch.update_one,
            filter,
            update,
            upsert=upsert,
            array_filters=array_filters,
            bypass_document_validation=bypass_document_validation,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session
        )

    def watch(
        self,
        pipeline: Optional[List[MutableMapping[str, Any]]] = None,
        *,
        full_document: Optional[str] = None,
        resume_after: Optional[Any] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[Collation] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[AsyncClientSession] = None,
        start_after: Optional[Any] = None
    ) -> "AsyncChangeStream":
        return AsyncChangeStream(
            self,
            pipeline,
            full_document,
            resume_after,
            max_await_time_ms,
            batch_size,
            collation,
            start_at_operation_time,
            session,
            start_after
        )

    def with_options(
        self,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[PREFERENCE] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None
    ) -> "AsyncCollection":
        self.dispatch = self.dispatch.with_options(
            codec_options=codec_options,
            read_preference=read_preference,
            write_concern=write_concern,
            read_concern=read_concern
        )

        return self

    @property
    def database(self) -> Database:
        return self.dispatch.database

    @property
    def full_name(self) -> str:
        return self.dispatch.full_name

    @property
    def name(self) -> str:
        return self.dispatch.name


class AsyncCursorBase(AsyncBase):
    """Base class for Cursor AsyncIOMongoDB instances

       *DEPRECATED* methods are removed in this class.
    """

    # each method is removed because we can iterate directly this class
    # And also we have to_list() method, so yeah kinda useless

    collection: AsyncCollection
    dispatch: Union["_LatentCursor", CommandCursor, Cursor, RawBatchCursor]
    loop: asyncio.AbstractEventLoop

    def __init__(
        self,
        cursor: Union["_LatentCursor", CommandCursor, Cursor, RawBatchCursor],
        collection: AsyncCollection = None
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

    async def __anext__(self) -> Any:
        if self.alive and (self._buffer_size() or await self._get_more()):
            return await util.run_sync(next, self.dispatch)
        raise StopAsyncIteration

    def _buffer_size(self) -> int:
        return len(self._data())

    def _query_flags(self) -> int:
        raise NotImplementedError

    def _data(self) -> Deque[Any]:
        raise NotImplementedError

    def _killed(self) -> None:
        raise NotImplementedError

    def _get_more(self) -> Coroutine[Any, Any, int]:
        if not self.alive:
            raise InvalidOperation(
                "Can't call get_more() on a AsyncCursor that has been"
                " exhausted or killed.")

        self.started = True
        return self._refresh()

    def _to_list(
        self,
        length: int,
        the_list: List[MutableMapping[str, Any]],
        future: asyncio.Future,
        get_more_future: asyncio.Future
    ) -> None:
        # get_more_future is the result of self._get_more().
        # future will be the result of the user's to_list() call.
        try:
            result = get_more_future.result()
            # Return early if the task was cancelled.
            if future.done():
                return
            collection = self.collection
            fix_outgoing = collection.database._fix_outgoing

            if length is None:
                n = result
            else:
                n = min(length, result)

            for _ in range(n):
                the_list.append(fix_outgoing(self._data().popleft(),
                                             collection))

            reached_length = (length is not None and len(the_list) >= length)
            if reached_length or not self.alive:
                future.set_result(the_list)
            else:
                new_future = self.loop.create_task(self._get_more())
                new_future.add_done_callback(
                    partial(
                        self.loop.call_soon_threadsafe,
                        self._to_list,
                        length,
                        the_list,
                        future
                    )
                )
        except Exception as exc:
            if not future.done():
                future.set_exception(exc)

    async def _refresh(self) -> int:
        return await util.run_sync(self.dispatch._refresh)

    def batch_size(self, batch_size) -> "AsyncCursorBase":
        self.dispatch.batch_size(batch_size)
        return self

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            await util.run_sync(self.dispatch.close)

    async def next(self) -> MutableMapping[str, Any]:
        return await self.__anext__()

    def to_list(self, length: int) -> asyncio.Future[List[MutableMapping[str, Any]]]:
        if length is not None and  length < 0:
                raise ValueError("length must be non-negative")

        if self._query_flags() & _QUERY_OPTIONS["tailable_cursor"]:
            raise InvalidOperation("Can't call to_list on tailable cursor")

        future = self.loop.create_future()
        the_list = []

        if not self.alive:
            future.set_result(the_list)
            return future

        get_more_future = self.loop.create_task(self._get_more())
        get_more_future.add_done_callback(
            partial(
                self.loop.call_soon_threadsafe,
                self._to_list,
                length,
                the_list,
                future
            )
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


class AsyncCommandCursor(AsyncCursorBase):
    """AsyncIO :obj:`~CommandCursor`

       *DEPRECATED* methods are removed in this class.
    """

    dispatch: CommandCursor

    def _query_flags(self):
        return 0

    def _data(self) -> Deque[Any]:
        return self.dispatch._CommandCursor__data

    def _killed(self) -> bool:
        return self.dispatch._CommandCursor__killed


class _LatentCursor:
    """Base class for LatentCursor AsyncIOMongoDB instance"""
    # ClassVar
    alive: ClassVar[bool] = True
    _AsyncCommandCursor__data: ClassVar[Deque[Any]] = deque()
    _AsyncCommandCursor__id: ClassVar[Optional[Any]] = None
    _AsyncCommandCursor__killed: ClassVar[bool] = False
    _AsyncCommandCursor__sock_mgr: ClassVar[Optional[Any]] = None
    _AsyncCommandCursor__session: ClassVar[Optional[AsyncClientSession]] = None
    _AsyncCommandCursor__explicit_session: ClassVar[Optional[bool]] = None
    address: ClassVar[Optional[Tuple[str, int]]] = None
    cursor_id: ClassVar[Optional[Any]] = None
    session: ClassVar[Optional[AsyncClientSession]] = None

    _AsyncCommandCursor__collection: AsyncCollection

    def __init__(self, collection: AsyncCollection) -> None:
        self._AsyncCommandCursor__collection = collection

    def _AsyncCommandCursor__end_session(self, *args: Any, **kwargs: Any) -> None:
        pass

    def _AsyncCommandCursor__die(self, *args: Any, **kwargs: Any) -> None:
        pass

    def _refresh(self) -> int:
        return 0

    def batch_size(self, _: int) -> None:
        pass

    def close(self) -> None:
        pass

    def clone(self) -> "_LatentCursor":
        return _LatentCursor(self._AsyncCommandCursor__collection)

    def rewind(self):
        pass

    @property
    def collection(self):
        return self._AsyncCommandCursor__collection


class AsyncLatentCommandCursor(AsyncCommandCursor):
    """Temporary Cursor for initializing in aggregate,
       and will be overwrite by :obj:`~asyncio.Future`"""

    dispatch: CommandCursor

    def __init__(
        self,
        collection: AsyncCollection,
        start: Callable[..., Coroutine[Any, Any, int]],
        *args: Any,
        **kwargs: Any
    ) -> None:
        self.start = start
        self.args = args
        self.kwargs = kwargs

        super().__init__(_LatentCursor(collection), collection)

    def batch_size(self, batch_size: int) -> "AsyncLatentCommandCursor":
        self.kwargs["batchSize"] = batch_size
        return self

    def _get_more(self) -> Union[asyncio.Future, Coroutine[Any, Any, int]]:
        if not self.started:
            self.started = True
            original_future = self.loop.create_future()
            future = self.loop.create_task(
                util.run_sync(self.start, *self.args, **self.kwargs))
            future.add_done_callback(
                partial(
                    self.loop.call_soon_threadsafe, self._on_started, original_future))

            return original_future

        return super()._get_more()

    def _on_started(
        self, original_future: asyncio.Future, future: asyncio.Future
    ) -> None:
        try:
            self.dispatch = future.result()
        except Exception as exc:
            if not original_future.done():
                original_future.set_exception(exc)
        else:
            # Return early if the task was cancelled.
            if original_future.done():
                return

            if self.dispatch._CommandCursor__data or not self.dispatch.alive:
                # _get_more is complete.
                original_future.set_result(len(self.dispatch._CommandCursor__data))
            else:
                # Send a getMore.
                fut = self._get_more()
                if isinstance(fut, asyncio.Future):

                    def copy(f: asyncio.Future) -> None:
                        if original_future.done():
                            return

                        exc = f.exception()
                        if exc is not None:
                            original_future.set_exception(exc)
                        else:
                            original_future.set_result(f.result())

                    fut.add_done_callback(copy)


class AsyncCursor(AsyncCursorBase):
    """AsyncIO :obj:`~Cursor`

       *DEPRECATED* methods are removed in this class.
    """

    dispatch: Cursor

    def add_option(self, mask: int) -> "AsyncCursor":
        self.dispatch = self.dispatch.add_option(mask)
        return self

    def allow_disk_use(self, allow_disk_use: bool) -> "AsyncCursor":
        self.dispatch = self.dispatch.allow_disk_use(allow_disk_use)
        return self

    def collation(self, collation: Collation) -> "AsyncCursor":
        self.dispatch = self.dispatch.collation(collation)
        return self

    def comment(self, comment: str) -> "AsyncCursor":
        self.dispatch = self.dispatch.comment(comment)
        return self

    async def distinct(self, key: str) -> List[Any]:
        return await util.run_sync(self.dispatch.distinct, key)

    async def explain(self) -> str:
        return await util.run_sync(self.dispatch.explain)

    def hint(self, index: Union[str, List[Tuple[str, Any]]]) -> "AsyncCursor":
        self.dispatch = self.dispatch.hint(index)
        return self

    def limit(self, limit: int) -> "AsyncCursor":
        self.dispatch = self.dispatch.limit(limit)
        return self

    def max(self, spec: List[Any]) -> "AsyncCursor":
        self.dispatch = self.dispatch.max(spec)
        return self

    def max_await_time_ms(self, max_await_time_ms: int) -> "AsyncCursor":
        self.dispatch = self.dispatch.max_await_time_ms(max_await_time_ms)
        return self

    def max_time_ms(self, max_time_ms: int) -> "AsyncCursor":
        self.dispatch = self.dispatch.max_time_ms(max_time_ms)
        return self

    def min(self, spec: List[Any]) -> "AsyncCursor":
        self.dispatch = self.dispatch.min(spec)
        return self

    def remove_option(self, mask: int) -> "AsyncCursor":
        self.dispatch = self.dispatch.remove_option(mask)
        return self

    def rewind(self) -> "AsyncCursor":
        self.dispatch = self.dispatch.rewind()
        return self

    def skip(self, skip: int) -> "AsyncCursor":
        self.dispatch = self.dispatch.skip(skip)
        return self

    def sort(
        self, key: Union[str, List[Tuple[str, Any]]], *, direction: Any = None
    ) -> "AsyncCursor":
        self.dispatch = self.dispatch.sort(key, direction=direction)
        return self

    def where(self, code: Code) -> "AsyncCursor":
        self.dispatch = self.dispatch.where(code)
        return self

    def _query_flags(self):
        return self.dispatch._Cursor__query_flags

    def _data(self):
        return self.dispatch._Cursor__data

    def _killed(self):
        return self.dispatch._Cursor__killed


class AsyncRawBatchCommandCursor(AsyncCursor):
    pass


class AsyncRawBatchCursor(AsyncCursor):
    pass


class AsyncChangeStream(AsyncBase):
    """AsyncIO :obj:`~ChangeStream`

       *DEPRECATED* methods are removed in this class.
    """

    _target: Union[AsyncClient, AsyncDB, AsyncCollection]

    dispatch: Optional[ChangeStream]

    def __init__(
        self,
        target: Union[AsyncClient, AsyncDB, AsyncCollection],
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

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

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
