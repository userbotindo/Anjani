"""Anjani database collection"""
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

from typing import Any, List, MutableMapping, Optional, Tuple, Union

from bson import CodecOptions
from bson.son import SON
from bson.timestamp import Timestamp
from pymongo import IndexModel
from pymongo.collation import Collation
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.read_concern import ReadConcern
from pymongo.results import (
    BulkWriteResult,
    DeleteResult,
    InsertManyResult,
    InsertOneResult,
    UpdateResult,
)
from pymongo.write_concern import WriteConcern

from anjani import util

from .base import AsyncBaseProperty
from .change_stream import AsyncChangeStream
from .client_session import AsyncClientSession
from .command_cursor import AsyncLatentCommandCursor
from .cursor import AsyncCursor, AsyncRawBatchCursor, Cursor
from .types import JavaScriptCode, ReadPreferences, Request


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
                self.read_concern,
            )
        )

    def aggregate(
        self,
        pipeline: List[MutableMapping[str, Any]],
        *,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> AsyncLatentCommandCursor:
        return AsyncLatentCommandCursor(
            self,
            self.dispatch.aggregate,
            pipeline,
            session=session.dispatch if session else session,
            **kwargs,
        )

    def aggregate_raw_batches(
        self,
        pipeline: List[MutableMapping[str, Any]],
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
        query: MutableMapping[str, Any],
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
        query: MutableMapping[str, Any],
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
        query: MutableMapping[str, Any],
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
        query: Optional[MutableMapping[str, Any]] = None,
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
        self, query: Optional[MutableMapping[str, Any]], *args: Any, **kwargs: Any
    ) -> Optional[MutableMapping[str, Any]]:
        return await util.run_sync(self.dispatch.find_one, query, *args, **kwargs)

    async def find_one_and_delete(
        self,
        query: MutableMapping[str, Any],
        *,
        projection: Optional[Union[List[Any], MutableMapping[str, Any]]] = None,
        sort: Optional[List[Tuple[str, Any]]] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> MutableMapping[str, Any]:
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
        query: MutableMapping[str, Any],
        replacement: MutableMapping[str, Any],
        *,
        projection: Optional[Union[List[Any], MutableMapping[str, Any]]] = None,
        sort: Optional[List[Tuple[str, Any]]] = None,
        upsert: bool = False,
        return_document: bool = False,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> MutableMapping[str, Any]:
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
        query: MutableMapping[str, Any],
        update: MutableMapping[str, Any],
        *,
        projection: Optional[Union[List[Any], MutableMapping[str, Any]]] = None,
        sort: Optional[List[Tuple[str, Any]]] = None,
        upsert: bool = False,
        return_document: bool = False,
        array_filters: Optional[List[MutableMapping[str, Any]]] = None,
        hint: Optional[Union[IndexModel, List[Tuple[str, Any]]]] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> MutableMapping[str, Any]:
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
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.index_information, session=session.dispatch if session else session
        )

    async def inline_map_reduce(
        self,
        mapping: JavaScriptCode,
        reduce: JavaScriptCode,
        *,
        full_response: bool = False,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.inline_map_reduce,
            mapping,
            reduce,
            full_response=full_response,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def insert_many(
        self,
        documents: List[MutableMapping[str, Any]],
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
        document: MutableMapping[str, Any],
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
        self, session: Optional[AsyncClientSession] = None
    ) -> AsyncLatentCommandCursor:
        return AsyncLatentCommandCursor(
            self, self.dispatch.list_indexes, session=session.dispatch if session else session
        )

    async def map_reduce(
        self,
        mapping: JavaScriptCode,
        reduce: JavaScriptCode,
        out: Union[str, MutableMapping[str, Any], SON],
        *,
        full_response: bool = False,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.map_reduce,
            mapping,
            reduce,
            out,
            full_response=full_response,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def options(
        self, session: Optional[AsyncClientSession] = None
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.options, session=session.dispatch if session else session
        )

    async def rename(
        self, new_name: str, *, session: Optional[AsyncClientSession] = None, **kwargs: Any
    ) -> MutableMapping[str, Any]:
        return await util.run_sync(
            self.dispatch.rename,
            new_name,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def replace_one(
        self,
        query: MutableMapping[str, Any],
        replacement: MutableMapping[str, Any],
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
        query: MutableMapping[str, Any],
        update: MutableMapping[str, Any],
        *,
        upsert: bool = False,
        array_filters: Optional[List[MutableMapping[str, Any]]] = None,
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
        query: MutableMapping[str, Any],
        update: MutableMapping[str, Any],
        *,
        upsert: bool = False,
        array_filters: Optional[List[MutableMapping[str, Any]]] = None,
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
        pipeline: Optional[List[MutableMapping[str, Any]]] = None,
        *,
        full_document: Optional[str] = None,
        resume_after: Optional[Any] = None,
        max_await_time_ms: Optional[int] = None,
        batch_size: Optional[int] = None,
        collation: Optional[Collation] = None,
        start_at_operation_time: Optional[Timestamp] = None,
        session: Optional[AsyncClientSession] = None,
        start_after: Optional[Any] = None,
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
    def database(self) -> Database:
        return self.dispatch.database

    @property
    def full_name(self) -> str:
        return self.dispatch.full_name

    @property
    def name(self) -> str:
        return self.dispatch.name
