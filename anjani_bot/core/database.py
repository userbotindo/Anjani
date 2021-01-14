"""Core database"""
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

import logging
from typing import List

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from motor.core import AgnosticCollection

from .. import Config

LOGGER = logging.getLogger(__name__)


class DataBase:
    """Client Database on MongoDB"""

    async def connect_db(self, db_name: str) -> None:
        """Connect to MongoDB client

        Parameters:
            db_name (`str`): Database name to log in. Will create new Database if not found.
        """
        LOGGER.info("Connecting to MongoDB...")
        self._client: AsyncIOMotorClient = AsyncIOMotorClient(Config.DB_URI)
        if db_name in await self._client.list_database_names():
            LOGGER.info("Database found, Logged in to Database...")
        else:
            LOGGER.info("Database not found! Creating New Database...")
        self._db: AsyncIOMotorDatabase = self._client[db_name]
        self._list_collection: List[str] = await self._db.list_collection_names()
        LOGGER.info("Database connected")

    async def disconnect_db(self) -> None:
        """Disconnect database client"""
        self._client.close()
        LOGGER.info("Disconnected from database")

    def get_collection(self, name: str) -> AgnosticCollection:
        """Get collection from database

        Parameters:
            name (`str`): Collection name to fetch
        """
        if name in self._list_collection:
            LOGGER.debug("Collection %s Found, fetching...", name)
        else:
            LOGGER.debug("Collection %s Not Found, Creating New Collection...", name)
        return self._db[name]
