"""Anjani base database"""
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

from bson.codec_options import CodecOptions
from bson.dbref import DBRef
from bson.son import SON
from bson.timestamp import Timestamp
from pymongo.collation import Collation
from pymongo.database import Database
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from anjani import util

from .base import AsyncBaseProperty
from .change_stream import AsyncChangeStream
from .client_session import AsyncClientSession
from .collection import AsyncCollection
from .command_cursor import AsyncCommandCursor, AsyncLatentCommandCursor, CommandCursor
from .typings import ReadPreferences

if TYPE_CHECKING:
    from .client import AsyncClient


class AsyncDatabase(AsyncBaseProperty):
    """AsyncIO :obj:`~Database`

    *DEPRECATED* methods are removed in this class.
    """

    _client: "AsyncClient"

    dispatch: Database

    def __init__(self, client: "AsyncClient", database: Database) -> None:
        self._client = client

        # Propagate initialization to base
        super().__init__(database)

    def __bool__(self) -> bool:
        return self.dispatch is not None

    def __getitem__(self, name) -> AsyncCollection:
        return AsyncCollection(self, name)

    def __hash__(self) -> int:
        return hash((self.client, self.name))

    def aggregate(
        self,
        pipeline: List[Mapping[str, Any]],
        *args: Any,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> AsyncLatentCommandCursor:
        return AsyncLatentCommandCursor(
            self["$cmd.aggregate"],
            self.dispatch.aggregate,
            pipeline,
            session=session.dispatch if session else session,
            *args,
            **kwargs,
        )

    async def command(
        self,
        command: Union[str, Mapping[str, Any]],
        *,
        value: int = 1,
        check: bool = True,
        allowable_errors: Optional[str] = None,
        read_preference: Optional[ReadPreferences] = None,
        codec_options: Optional[CodecOptions] = None,
        session: Optional[AsyncClientSession] = None,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        return await util.run_sync(
            self.dispatch.command,
            command,
            value=value,
            check=check,
            allowable_errors=allowable_errors,
            read_preference=read_preference,
            codec_options=codec_options,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def close(self) -> None:
        await self._client.close()

    async def create_collection(
        self,
        name: str,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[ReadPreferences] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
        session: Optional[AsyncClientSession] = None,
        check_exists: bool = True,
        **kwargs: Any,
    ) -> AsyncCollection:
        return AsyncCollection(
            self,
            name,
            collection=await util.run_sync(
                self.dispatch.create_collection,
                name,
                codec_options=codec_options,
                read_preference=read_preference,
                write_concern=write_concern,
                read_concern=read_concern,
                session=session.dispatch if session else session,
                check_exists=check_exists,
                **kwargs,
            ),
            session=session,
        )

    async def dereference(
        self, dbref: DBRef, *, session: Optional[AsyncClientSession] = None, **kwargs: Any
    ) -> Optional[Mapping[str, Any]]:
        return await util.run_sync(
            self.dispatch.dereference,
            dbref,
            session=session.dispatch if session else session,
            **kwargs,
        )

    async def drop_collection(
        self,
        name_or_collection: Union[str, AsyncCollection],
        session: Optional[AsyncClientSession] = None,
    ) -> Mapping[str, Any]:
        if isinstance(name_or_collection, AsyncCollection):
            name_or_collection = name_or_collection.name

        return await util.run_sync(
            self.dispatch.drop_collection,
            name_or_collection,
            session=session.dispatch if session else session,
        )

    def get_collection(
        self,
        name: str,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[ReadPreferences] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ) -> AsyncCollection:
        return AsyncCollection(
            self,
            name,
            codec_options=codec_options,
            read_preference=read_preference,
            write_concern=write_concern,
            read_concern=read_concern,
        )

    async def list_collection_names(
        self,
        *,
        session: Optional[AsyncClientSession] = None,
        query: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> List[str]:
        return await util.run_sync(
            self.dispatch.list_collection_names,
            session=session.dispatch if session else session,
            filter=query,
            **kwargs,
        )

    async def list_collections(
        self,
        *,
        session: Optional[AsyncClientSession] = None,
        query: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> AsyncCommandCursor:
        cmd = SON([("listCollections", 1)])
        cmd.update(query, **kwargs)

        res: Mapping[str, Any] = await util.run_sync(
            self.dispatch._retryable_read_command,  # skipcq: PYL-W0212
            cmd,
            session=session.dispatch if session else session,
        )
        return AsyncCommandCursor(CommandCursor(self["$cmd"], res["cursor"], None))

    async def validate_collection(
        self,
        name_or_collection: Union[str, AsyncCollection],
        *,
        scandata: bool = False,
        full: bool = False,
        session: Optional[AsyncClientSession] = None,
        background: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        if isinstance(name_or_collection, AsyncCollection):
            name_or_collection = name_or_collection.name

        return await util.run_sync(
            self.dispatch.validate_collection,
            name_or_collection,
            scandata=scandata,
            full=full,
            session=session.dispatch if session else session,
            background=background,
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
    ) -> "AsyncDatabase":
        self.dispatch = self.dispatch.with_options(
            codec_options=codec_options,
            read_preference=read_preference,
            write_concern=write_concern,
            read_concern=read_concern,
        )

        return self

    @property
    def client(self) -> "AsyncClient":
        return self._client

    @property
    def name(self) -> str:
        return self.dispatch.name
