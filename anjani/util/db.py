from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Callable,
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
from bson.son import SON
from pymongo import (
    DeleteOne,
    IndexModel,
    InsertOne,
    MongoClient,
    ReplaceOne
)
from pymongo.client_session import ClientSession, SessionOptions
from pymongo.collation import Collation
from pymongo.collection import Collection
from pymongo.command_cursor import CommandCursor as _CommandCursor
from pymongo.cursor import Cursor as _Cursor
from pymongo.database import Database
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
Requests = Union[DeleteOne, InsertOne, ReplaceOne]
Results = TypeVar("Results")


class Cursor(_Cursor):

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


class CommandCursor(_CommandCursor):

    def __init__(
        self,
        collection: "AsyncCollection",
        cursor_info: MutableMapping[str, Any],
        address: Union[Tuple[str, int], None],
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
            session=session,
            explicit_session=explicit_session,
        )

    @property
    def _AsyncCommandCursor__data(self) -> Deque[Any]:
        return self.__data

    async def _AsyncCommandCursor__die(self, synchronous: bool = False) -> None:
        await util.run_sync(self.__die, synchronous=synchronous)

    @property
    def _AsyncCommandCursor__killed(self) -> bool:
        return self.__killed


class AsyncClientSession:
    # All DEPRECATED methods are removed in this class.

    _client: "AsyncClient"
    _session: ClientSession

    def __init__(self, client: "AsyncClient", session: ClientSession) -> None:
        self._client = client
        self._session = session

    async def __aenter__(self) -> "AsyncClientSession":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.end_session()

    async def abort_transaction(self) -> None:
        return await util.run_sync(self._session.abort_transaction)

    async def commit_transaction(self) -> None:
        return await util.run_sync(self._session.commit_transaction)

    async def end_session(self) -> None:
        return await util.run_sync(self._session.end_session)

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
            self._session.start_transaction,
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
        finally:
            await self.end_session()

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
        self._session.advance_cluster_time(cluster_time=cluster_time)

    def advance_operation_time(self, operation_time: int) -> None:
        self._session.advance_operation_time(operation_time=operation_time)

    @property
    def client(self) -> "AsyncClient":
        return self._client

    @property
    def cluster_time(self) -> Optional[int]:
        return self._session.cluster_time

    @property
    def has_ended(self) -> bool:
        return self._session.has_ended

    @property
    def in_transaction(self) -> bool:
        return self._session.in_transaction

    @property
    def operation_time(self) -> Optional[int]:
        return self._session.operation_time

    @property
    def options(self) -> SessionOptions:
        return self._session.options

    @property
    def session_id(self) -> MutableMapping[str, Any]:
        return self._session.session_id


class AsyncClient:
    # TODO:
    # - Add watch method

    # All DEPRECATED methods are removed in this class.

    _client: MongoClient

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._client = MongoClient(*args, **kwargs)

    async def close(self) -> None:
        await util.run_sync(self._client.close)

    async def drop_database(
        self,
        name_or_database: Union[str, "AsyncDB"],
        session: Optional[AsyncClientSession] = None
    ) -> None:
        if isinstance(name_or_database, AsyncDB):
            name_or_database = name_or_database.name

        return await util.run_sync(
            self._client.drop_database,
            name_or_database,
            session=session
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
            self._client.get_database(
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
            self._client.get_default_database(
                default,
                codec_options=codec_options,
                read_preference=read_preference,
                write_concern=write_concern,
                read_concern=read_concern
            )
        )

    async def list_database_names(
        self, session: Optional[AsyncClientSession] = None) -> List[str]:
        return await util.run_sync(self._client.list_database_names,
                                   session=session)

    async def list_databases(
        self, session: Optional[AsyncClientSession] = None, **kwargs: Any
    ) -> "AsyncCommandCursor":
        cmd = SON([("listDatabases", 1)])
        cmd.update(kwargs)
        database = self.get_database("admin",
                                     codec_options=DEFAULT_CODEC_OPTIONS,
                                     read_preference=ReadPreference.PRIMARY,
                                     write_concern=DEFAULT_WRITE_CONCERN)
        res: MutableMapping[str, Any]
        res = await util.run_sync(
            database._db._retryable_read_command, cmd, session=session)
        cursor: MutableMapping[str, Any] = {
            "id": 0,
            "firstBatch": res["databases"],
            "ns": "admin.$cmd",
        }
        return AsyncCommandCursor(CommandCursor(database["$cmd"], cursor, None))

    async def server_info(
        self, session: Optional[AsyncClientSession] = None
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(self._client.server_info, session=session)

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
        session = self._client.start_session(
            causal_consistency=causal_consistency,
            default_transaction_options=default_transaction_options,
            snapshot=snapshot
        )

        async with AsyncClientSession(self, session) as session:
            yield session

    async def watch(self):  # TODO
        raise NotImplementedError

    @property
    def HOST(self) -> str:
        return self._client.HOST

    @property
    def PORT(self) -> int:
        return self._client.PORT

    @property
    def address(self) -> Optional[Tuple[str, int]]:
        return self._client.address

    @property
    def arbiters(self) -> Set[Tuple[str, int]]:
        return self._client.arbiters

    @property
    def codec_options(self) -> CodecOptions:
        return self._client.codec_options

    @property
    def event_listeners(self) -> Any:
        return self._client.event_listeners

    @property
    def is_mongos(self) -> bool:
        return self._client.is_mongos

    @property
    def is_primary(self) -> bool:
        return self._client.is_primary

    @property
    def local_threshold_ms(self) -> int:
        return self._client.local_threshold_ms

    @property
    def max_bson_size(self) -> int:
        return self._client.max_bson_size

    @property
    def max_idle_time_ms(self) -> Optional[int]:
        return self._client.max_idle_time_ms

    @property
    def max_message_size(self) -> int:
        return self._client.max_message_size

    @property
    def max_pool_size(self) -> int:
        return self._client.max_pool_size

    @property
    def max_write_batch_size(self) -> int:
        return self._client.max_write_batch_size

    @property
    def min_pool_size(self) -> int:
        return self._client.min_pool_size

    @property
    def nodes(self) -> FrozenSet[Set[Tuple[str, int]]]:
        return self._client.nodes

    @property
    def primary(self) -> Optional[Tuple[str, int]]:
        return self._client.primary

    @property
    def read_concern(self) -> ReadConcern:
        return self._client.read_concern

    @property
    def read_preference(self) -> _ServerMode:
        return self._client.read_preference

    @property
    def retry_reads(self) -> bool:
        return self._client.retry_reads

    @property
    def retry_writes(self) -> bool:
        return self._client.retry_writes

    @property
    def secondaries(self) -> Set[Tuple[str, int]]:
        return self._client.secondaries

    @property
    def server_selection_timeout(self) -> int:
        return self._client.server_selection_timeout

    @property
    def topology_description(self) -> TopologyDescription:
        return self._client.topology_description

    @property
    def write_concern(self) -> WriteConcern:
        return self._client.write_concern

class AsyncDB:
    # TODO:
    # - Add watch method

    # All DEPRECATED methods are removed in this class.

    _client: AsyncClient
    _db: Database

    def __init__(self, client: AsyncClient, database: Database) -> None:
        self._client = client
        self._db = database

    def __getitem__(self, name) -> "AsyncCollection":
        return AsyncCollection(Collection(self._db, name))

    def __repr__(self):
        return f"AsyncDatabase({self.client}, {self.name})"

    async def watch(self) -> None:  # TODO
        raise NotImplementedError

    def aggregate(
        self,
        pipeline: Tuple[Any, ...],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> "AsyncCommandCursor":
        return AsyncCommandCursor(
            self._db.aggregate(
                pipeline,
                session=session,
                **kwargs
            )
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
        return await self._db.command(
            command,
            value=value,
            check=check,
            allowable_errors=allowable_errors,
            read_preference=read_preference,
            codec_options=codec_options,
            session=session,
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
                self._db.create_collection,
                name,
                codec_options=codec_options,
                read_preference=read_preference,
                write_concern=write_concern,
                read_concern=read_concern,
                session=session,
                **kwargs
            )
        )

    async def dereference(
        self, dbref: DBRef, *, session: Optional[AsyncClientSession] = None, **kwargs: Any
    ) -> Optional[MutableMapping[str, Any]]:
        return await util.run_sync(self._db.dereference, dbref, session=session, **kwargs)

    async def drop_collection(
        self,
        name_or_collection: Union[str, "AsyncCollection"],
        session: Optional[AsyncClientSession] = None
    ) -> MutableMapping[str, Any]:
        if isinstance(name_or_collection, AsyncCollection):
            name_or_collection = name_or_collection.name

        return await util.run_sync(
            self._db.drop_collection,
            name_or_collection,
            session=session
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
            self._db.get_collection(
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
            self._db.list_collection_names,
            session=session,
            filter=filter,
            **kwargs
        )

    # Lazy method
    async def list_collections(
        self,
        *,
        session: Optional[AsyncClientSession] = None,
        filter: Optional[MutableMapping[str, Any]] = None,
        **kwargs: Any
    ) -> "AsyncCommandCursor":
        return AsyncCommandCursor(
            await util.run_sync(
                self._db.list_collections,
                session=session,
                filter=filter,
                **kwargs
            )
        )

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
            self._db.validate_collection,
            name_or_collection,
            scandata=scandata,
            full=full,
            session=session,
            background=background
        )

    def with_options(
        self,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[PREFERENCE] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None
    ) -> "AsyncDB":
        self._db = self._db.with_options(
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
    def codec_options(self) -> CodecOptions:
        return self._db.codec_options

    @property
    def name(self) -> str:
        return self._db.name

    @property
    def read_concern(self) -> ReadConcern:
        return self._db.read_concern

    @property
    def read_preference(self) -> _ServerMode:
        return self._db.read_preference

    @property
    def write_concern(self) -> WriteConcern:
        return self._db.write_concern


class AsyncCollection:
    # TODO:
    # - Add aggregate_raw_batches method
    # - Add find_raw_batches method
    # - Add inline_map_reduce method
    # - Add list_indexes method
    # - Add map_reduce method
    # - Add watch method

    # All DEPRECATED methods are removed in this class.

    _col: Collection

    def __init__(self, collection: Collection) -> None:
        self._col = collection

    def __getitem__(self, name) -> "AsyncCollection":
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

    def __repr__(self):
        return f"AsyncCollection({self.database}, {self.name})"

    def aggregate(
        self,
        pipeline: Tuple[Any, ...],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> "AsyncCommandCursor":
        return AsyncCommandCursor(
            self._col.aggregate(
                pipeline,
                session=session,
                **kwargs
            )
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
            self._col.bulk_write,
            request,
            ordered=ordered,
            bypass_document_validation=bypass_document_validation,
            session=session
        )

    async def count_documents(
        self,
        filter: MutableMapping[str, Any],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> int:
        return await util.run_sync(
            self._col.count_documents,
            filter,
            session=session,
            **kwargs
        )

    async def create_index(
        self, keys: Union[str, List[Tuple[str, Any]]], **kwargs: Any
    ) -> str:
        return await util.run_sync(
            self._col.create_index,
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
            self._col.create_indexes,
            indexes,
            session=session,
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
            self._col.delete_many,
            filter,
            collation=collation,
            hint=hint,
            session=session
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
            self._col.delete_one,
            filter,
            collation=collation,
            hint=hint,
            session=session
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
            self._col.distinct,
            key,
            filter=filter,
            session=session,
            **kwargs
        )

    async def drop(self, session: Optional[AsyncClientSession] = None) -> None:
        await util.run_sync(self._col.drop, session=session)

    async def drop_index(
        self,
        index_or_name: Union[str, IndexModel],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> None:
        await util.run_sync(self._col.drop_index,
                            index_or_name,
                            session=session,
                            **kwargs)

    async def drop_indexes(self, session: Optional[AsyncClientSession] = None, **kwargs) -> None:
        await util.run_sync(self._col.drop_indexes, session=session, **kwargs)

    async def estimated_document_count(self, **kwargs: Any) -> int:
        return await util.run_sync(self._col.estimated_document_count, **kwargs)

    def find(self, *args: Any, **kwargs: Any) -> AsyncIterator[MutableMapping[str, Any]]:
        return AsyncCursor(Cursor(self._col, *args, **kwargs))

    async def find_one(
        self,
        filter: Optional[MutableMapping[str, Any]] = None,
        *args: Any,
        **kwargs: Any
    ) -> Optional[MutableMapping[str, Any]]:
        return await util.run_sync(
            self._col.find_one, filter, *args, **kwargs)

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
            self._col.find_one_and_delete,
            filter,
            projection=projection,
            sort=sort,
            hint=hint,
            session=session,
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
            self._col.find_one_and_replace,
            filter,
            replacement,
            projection=projection,
            sort=sort,
            upsert=upsert,
            return_document=return_document,
            hint=hint,
            session=session,
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
            self._col.find_one_and_update,
            filter,
            update,
            projection=projection,
            sort=sort,
            upsert=upsert,
            return_document=return_document,
            array_filters=array_filters,
            hint=hint,
            session=session,
            **kwargs
        )

    async def index_information(
        self, session: Optional[AsyncClientSession] = None
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(self._col.index_information, session=session)

    async def insert_many(
        self,
        documents: List[MutableMapping[str, Any]],
        *,
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: Optional[AsyncClientSession] = None
    ) -> InsertManyResult:
        return await util.run_sync(
            self._col.insert_many,
            documents,
            ordered=ordered,
            bypass_document_validation=bypass_document_validation,
            session=session
        )

    async def insert_one(
        self,
        document: MutableMapping[str, Any],
        *,
        bypass_document_validation: bool = False,
        session: Optional[AsyncClientSession] = None
    ) -> InsertOneResult:
        return await util.run_sync(
            self._col.insert_one,
            document,
            bypass_document_validation=bypass_document_validation,
            session=session
        )

    async def options(
        self, session: Optional[AsyncClientSession] = None
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(self._col.options, session=session)

    async def rename(
        self,
        new_name: str,
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self._col.rename,
            new_name,
            session=session,
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
            self._col.replace_one,
            filter,
            replacement,
            upsert=upsert,
            bypass_document_validation=bypass_document_validation,
            collation=collation,
            hint=hint,
            session=session
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
            self._col.update_many,
            filter,
            update,
            upsert=upsert,
            array_filters=array_filters,
            bypass_document_validation=bypass_document_validation,
            collation=collation,
            hint=hint,
            session=session
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
            self._col.update_one,
            filter,
            update,
            upsert=upsert,
            array_filters=array_filters,
            bypass_document_validation=bypass_document_validation,
            collation=collation,
            hint=hint,
            session=session
        )

    def with_options(
        self,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[PREFERENCE] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None
    ) -> "AsyncCollection":
        self._col = self._col.with_options(
            codec_options=codec_options,
            read_preference=read_preference,
            write_concern=write_concern,
            read_concern=read_concern
        )

        return self
        
    @property
    def codec_options(self) -> CodecOptions:
        return self._col.codec_options

    @property
    def database(self) -> Database:
        return self._col.database

    @property
    def full_name(self) -> str:
        return self._col.full_name

    @property
    def name(self) -> str:
        return self._col.name

    @property
    def read_concern(self) -> ReadConcern:
        return self._col.read_concern

    @property
    def read_preference(self) -> _ServerMode:
        return self._col.read_preference

    @property
    def write_concern(self) -> WriteConcern:
        return self._col.write_concern


class AgnosticAsyncCursor:
    # All DEPRECATED methods are removed in this class.

    # Non Deprecated removed methods are:
    # - each
    # - batch_size
    # - to_list

    _cursor: Union[CommandCursor, Cursor]

    def __init__(self, cursor: Union[CommandCursor, Cursor]) -> None:
        self._cursor = cursor

        self.started = False
        self.closed = False

    def __aiter__(self) -> "AgnosticAsyncCursor":
        return self

    async def __anext__(self) -> Any:
        try:
            if self.alive and (self._buffer_size() or await self._get_more()):
                return await util.run_sync(next, self._cursor)
        except AttributeError:  # Lazy hack to implement in aggregate and list_collections
            if self.alive and await self._get_more():
                return await util.run_sync(next, self._cursor)
        raise StopAsyncIteration

    def _buffer_size(self) -> int:
        return len(self._data())

    def _query_flags(self) -> None:
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
        return util.run_sync(self._cursor._refresh)

    async def next(self) -> MutableMapping[str, Any]:
        return await self.__anext__()

    async def close(self) -> None:
        if not self.closed:
            self.closed = True
            await util.run_sync(self._cursor.close)

    @property
    def address(self) -> Optional[str]:
        return self._cursor.address

    @property
    def alive(self) -> bool:
        if not self._cursor:
            return True
        return self._cursor.alive

    @property
    def cursor_id(self) -> Optional[int]:
        return self._cursor.cursor_id

    @property
    def session(self) -> Optional[AsyncClientSession]:
        return self._cursor.session


class AsyncCommandCursor(AgnosticAsyncCursor):
    # TODO:
    # Implement this class into:
    #     - list_collections
    #     - aggregate (both in AsyncDB and AsyncCollection)

    _cursor: CommandCursor

    def _query_flags(self):
        return 0

    def _data(self) -> Deque[Any]:
        return self._cursor.__data

    def _killed(self) -> bool:
        return self._cursor.__killed


class AsyncCursor(AgnosticAsyncCursor):
    # All DEPRECATED methods are removed in this class.

    _cursor: Cursor

    def add_option(self, mask: int) -> "AsyncCursor":
        self._cursor = self._cursor.add_option(mask)
        return self

    def allow_disk_use(self, allow_disk_use: bool) -> "AsyncCursor":
        self._cursor = self._cursor.allow_disk_use(allow_disk_use)
        return self

    def collation(self, collation: Collation) -> "AsyncCursor":
        self._cursor = self._cursor.collation(collation)
        return self

    def comment(self, comment: str) -> "AsyncCursor":
        self._cursor = self._cursor.comment(comment)
        return self

    async def distinct(self, key: str) -> List[Any]:
        return await util.run_sync(self._cursor.distinct, key)

    async def explain(self) -> str:
        return await util.run_sync(self._cursor.explain)

    def hint(self, index: Union[str, List[Tuple[str, Any]]]) -> "AsyncCursor":
        self._cursor = self._cursor.hint(index)
        return self

    def limit(self, limit: int) -> "AsyncCursor":
        self._cursor = self._cursor.limit(limit)
        return self

    def max(self, spec: List[Any]) -> "AsyncCursor":
        self._cursor = self._cursor.max(spec)
        return self

    def max_await_time_ms(self, max_await_time_ms: int) -> "AsyncCursor":
        self._cursor = self._cursor.max_await_time_ms(max_await_time_ms)
        return self

    def max_time_ms(self, max_time_ms: int) -> "AsyncCursor":
        self._cursor = self._cursor.max_time_ms(max_time_ms)
        return self

    def min(self, spec: List[Any]) -> "AsyncCursor":
        self._cursor = self._cursor.min(spec)
        return self

    def remove_option(self, mask: int) -> "AsyncCursor":
        self._cursor = self._cursor.remove_option(mask)
        return self

    def rewind(self) -> "AsyncCursor":
        self._cursor = self._cursor.rewind()
        return self

    def skip(self, skip: int) -> "AsyncCursor":
        self._cursor = self._cursor.skip(skip)
        return self

    def sort(
        self, key: Union[str, List[Tuple[str, Any]]], *, direction: Any = None
    ) -> "AsyncCursor":
        self._cursor = self._cursor.sort(key, direction=direction)
        return self

    def where(self, code: Code) -> "AsyncCursor":
        self._cursor = self._cursor.where(code)
        return self

    def _query_flags(self):
        return self._cursor.__query_flags

    def _data(self):
        return self._cursor.__data

    def _killed(self):
        return self._cursor.__killed
