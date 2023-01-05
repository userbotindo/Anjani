"""Anjani database collection"""
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

from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    List,
    Literal,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from bson.codec_options import CodecOptions
from bson.timestamp import Timestamp
from pymongo.collation import Collation
from pymongo.collection import Collection
from pymongo.operations import IndexModel
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import _ServerMode
from pymongo.results import (
    BulkWriteResult,
    DeleteResult,
    InsertManyResult,
    InsertOneResult,
    UpdateResult,
)
from pymongo.typings import _DocumentType
from pymongo.write_concern import WriteConcern

from anjani import util

from .base import AsyncBaseProperty
from .change_stream import AsyncChangeStream
from .client_session import AsyncClientSession
from .command_cursor import AsyncLatentCommandCursor
from .cursor import AsyncCursor, AsyncRawBatchCursor, Cursor
from .typings import ReadPreferences, Request

if TYPE_CHECKING:
    from .db import AsyncDatabase


class AsyncCollection(AsyncBaseProperty, Generic[_DocumentType]):
    """AsyncIO :obj:`~Collection`

    *DEPRECATED* methods are removed in this class.
    """

    database: "AsyncDatabase"
    dispatch: Collection

    def __init__(
        self,
        database: "AsyncDatabase",
        name: str,
        *,
        create: bool = False,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[_ServerMode] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
        collection: Optional[Collection] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> None:
        dispatch = (
            collection
            if collection is not None
            else Collection(
                database.dispatch,
                name,
                create=create,
                codec_options=codec_options,
                read_preference=read_preference,
                write_concern=write_concern,
                read_concern=read_concern,
                session=session.dispatch if session else session,
                **kwargs,
            )
        )
        # Propagate initialization to base
        super().__init__(dispatch)
        self.database = database

    def __bool__(self) -> bool:
        return self.dispatch is not None

    def __getitem__(self, name: str) -> "AsyncCollection":
        return AsyncCollection(
            self.database,
            f"{self.name}.{name}",
            collection=self.dispatch[name],
        )

    def __hash__(self) -> int:
        return hash((self.database, self.name))

    def aggregate(
        self,
        pipeline: List[Mapping[str, Any]],
        *args: Any,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> AsyncLatentCommandCursor:
        return AsyncLatentCommandCursor(
            self,
            self.dispatch.aggregate,
            pipeline,
            session=session.dispatch if session else session,
            *args,
            **kwargs,
        )

    def aggregate_raw_batches(
        self,
        pipeline: List[Mapping[str, Any]],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> AsyncLatentCommandCursor:
        return AsyncLatentCommandCursor(
            self,
            self.dispatch.aggregate_raw_batches,
            pipeline,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def bulk_write(
        self,
        request: List[Request],
        *,
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: Optional[AsyncClientSession] = None,
    ) -> BulkWriteResult:
        return await util.run_sync(
            self.dispatch.bulk_write,
            request,
            ordered=ordered,
            bypass_document_validation=bypass_document_validation,
            session=session.dispatch if session else session,
        )

    async def count_documents(
        self,
        query: Mapping[str, Any],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> int:
        return await util.run_sync(
            self.dispatch.count_documents,
            query,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def create_index(self, keys: Union[str, List[Tuple[str, Any]]], **kwargs: Any) -> str:
        return await util.run_sync(self.dispatch.create_index, keys, **kwargs)

    async def create_indexes(
        self,
        indexes: List[IndexModel],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> List[str]:
        return await util.run_sync(
            self.dispatch.create_indexes,
            indexes,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def delete_many(
        self,
        query: Mapping[str, Any],
        *,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
    ) -> DeleteResult:
        return await util.run_sync(
            self.dispatch.delete_many,
            query,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session,
        )

    async def delete_one(
        self,
        query: Mapping[str, Any],
        *,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
    ) -> DeleteResult:
        return await util.run_sync(
            self.dispatch.delete_one,
            query,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session,
        )

    async def distinct(
        self,
        key: str,
        query: Optional[Mapping[str, Any]] = None,
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> List[str]:
        return await util.run_sync(
            self.dispatch.distinct,
            key,
            filter=query,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def drop(self, session: Optional[AsyncClientSession] = None) -> None:
        await util.run_sync(self.dispatch.drop, session=session.dispatch if session else session)

    async def drop_index(
        self,
        index_or_name: Union[str, IndexModel],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> None:
        await util.run_sync(
            self.dispatch.drop_index,
            index_or_name,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def drop_indexes(self, session: Optional[AsyncClientSession] = None, **kwargs) -> None:
        await util.run_sync(
            self.dispatch.drop_indexes, session=session.dispatch if session else session, **kwargs
        )

    async def estimated_document_count(self, **kwargs: Any) -> int:
        return await util.run_sync(self.dispatch.estimated_document_count, **kwargs)

    def find(self, *args: Any, **kwargs: Any) -> AsyncCursor:
        return AsyncCursor(Cursor(self, *args, **kwargs), self)

    async def find_one(
        self, query: Optional[Mapping[str, Any]], *args: Any, **kwargs: Any
    ) -> Optional[Mapping[str, Any]]:
        return await util.run_sync(self.dispatch.find_one, query, *args, **kwargs)

    async def find_one_and_delete(
        self,
        query: Mapping[str, Any],
        *,
        projection: Optional[Union[List[Any], Mapping[str, Any]]] = None,
        sort: Optional[List[Tuple[str, Any]]] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        return await util.run_sync(
            self.dispatch.find_one_and_delete,
            query,
            projection=projection,
            sort=sort,
            hint=hint,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def find_one_and_replace(
        self,
        query: Mapping[str, Any],
        replacement: Mapping[str, Any],
        *,
        projection: Optional[Union[List[Any], Mapping[str, Any]]] = None,
        sort: Optional[List[Tuple[str, Any]]] = None,
        upsert: bool = False,
        return_document: bool = False,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        return await util.run_sync(
            self.dispatch.find_one_and_replace,
            query,
            replacement,
            projection=projection,
            sort=sort,
            upsert=upsert,
            return_document=return_document,
            hint=hint,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def find_one_and_update(
        self,
        query: Mapping[str, Any],
        update: Mapping[str, Any],
        *,
        projection: Optional[Union[List[Any], Mapping[str, Any]]] = None,
        sort: Optional[List[Tuple[str, Any]]] = None,
        upsert: bool = False,
        return_document: bool = False,
        array_filters: Optional[List[Mapping[str, Any]]] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        return await util.run_sync(
            self.dispatch.find_one_and_update,
            query,
            update,
            projection=projection,
            sort=sort,
            upsert=upsert,
            return_document=return_document,
            array_filters=array_filters,
            hint=hint,
            session=session.dispatch if session else session,
            **kwargs,
        )

    def find_raw_batches(self, *args: Any, **kwargs: Any) -> AsyncRawBatchCursor:
        if "session" in kwargs:
            session = kwargs["session"]
            kwargs["session"] = session.dispatch if session else session

        cursor = self.dispatch.find_raw_batches(*args, **kwargs)

        return AsyncRawBatchCursor(cursor, self)

    async def index_information(
        self, session: Optional[AsyncClientSession] = None
    ) -> Mapping[str, Any]:
        return await util.run_sync(
            self.dispatch.index_information, session=session.dispatch if session else session
        )

    async def insert_many(
        self,
        documents: List[Mapping[str, Any]],
        *,
        ordered: bool = True,
        bypass_document_validation: bool = False,
        session: Optional[AsyncClientSession] = None,
    ) -> InsertManyResult:
        return await util.run_sync(
            self.dispatch.insert_many,
            documents,
            ordered=ordered,
            bypass_document_validation=bypass_document_validation,
            session=session.dispatch if session else session,
        )

    async def insert_one(
        self,
        document: Mapping[str, Any],
        *,
        bypass_document_validation: bool = False,
        session: Optional[AsyncClientSession] = None,
    ) -> InsertOneResult:
        return await util.run_sync(
            self.dispatch.insert_one,
            document,
            bypass_document_validation=bypass_document_validation,
            session=session.dispatch if session else session,
        )

    def list_indexes(
        self, *args: Any, session: Optional[AsyncClientSession] = None, **kwargs: Any
    ) -> AsyncLatentCommandCursor:
        return AsyncLatentCommandCursor(
            self,
            self.dispatch.list_indexes,
            session=session.dispatch if session else session,
            *args,
            **kwargs,
        )

    async def options(self, session: Optional[AsyncClientSession] = None) -> Mapping[str, Any]:
        return await util.run_sync(
            self.dispatch.options, session=session.dispatch if session else session
        )

    async def rename(
        self, new_name: str, *, session: Optional[AsyncClientSession] = None, **kwargs: Any
    ) -> Mapping[str, Any]:
        return await util.run_sync(
            self.dispatch.rename,
            new_name,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def replace_one(
        self,
        query: Mapping[str, Any],
        replacement: Mapping[str, Any],
        *,
        upsert: bool = False,
        bypass_document_validation: bool = False,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
    ) -> UpdateResult:
        return await util.run_sync(
            self.dispatch.replace_one,
            query,
            replacement,
            upsert=upsert,
            bypass_document_validation=bypass_document_validation,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session,
        )

    async def update_many(
        self,
        query: Mapping[str, Any],
        update: Mapping[str, Any],
        *,
        upsert: bool = False,
        array_filters: Optional[List[Mapping[str, Any]]] = None,
        bypass_document_validation: bool = False,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
    ) -> UpdateResult:
        return await util.run_sync(
            self.dispatch.update_many,
            query,
            update,
            upsert=upsert,
            array_filters=array_filters,
            bypass_document_validation=bypass_document_validation,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session,
        )

    async def update_one(
        self,
        query: Mapping[str, Any],
        update: Mapping[str, Any],
        *,
        upsert: bool = False,
        array_filters: Optional[List[Mapping[str, Any]]] = None,
        bypass_document_validation: bool = False,
        collation: Optional[Collation] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
    ) -> UpdateResult:
        return await util.run_sync(
            self.dispatch.update_one,
            query,
            update,
            upsert=upsert,
            array_filters=array_filters,
            bypass_document_validation=bypass_document_validation,
            collation=collation,
            hint=hint,
            session=session.dispatch if session else session,
        )

    def watch(
        self,
        pipeline: Optional[List[Mapping[str, Any]]] = None,
        *,
        full_document: Optional[Literal["updateLookup"]] = None,
        resume_after: Optional[Mapping[str, str]] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[Collation] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[AsyncClientSession] = None,
        start_after: Optional[Mapping[str, str]] = None,
        comment: Optional[str] = None,
        full_document_before_change: Optional[Literal["required", "whenAvailable"]] = None,
    ) -> AsyncChangeStream:
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
            start_after,
            comment,
            full_document_before_change,
        )

    def with_options(
        self,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[ReadPreferences] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> "AsyncCollection":
        self.dispatch = self.dispatch.with_options(
            codec_options=codec_options,
            read_preference=read_preference,
            write_concern=write_concern,
            read_concern=read_concern,
        )

        return self

    @property
    def full_name(self) -> str:
        return self.dispatch.full_name

    @property
    def name(self) -> str:
        return self.dispatch.name
