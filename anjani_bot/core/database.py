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

# pylint: disable=unsubscriptable-object

import logging
from codecs import decode, encode
from typing import List

from yaml import full_load
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from motor.core import AgnosticCollection

from .. import Config

LOGGER = logging.getLogger(__name__)


class DataBase:
    """Client Database on MongoDB"""

    def _load_language(self):
        """Load bot language."""
        # pylint: disable=attribute-defined-outside-init
        LOGGER.info("Loading language...")
        self.__language = ['en', 'id']
        self.__strings = {}
        for i in self.__language:
            LOGGER.debug("Loading language: %s", i)
            self.__strings[i] = full_load(open(f"anjani_bot/core/language/{i}.yml", "r"))
        LOGGER.info("Language %s loaded", self.__language)

    async def connect_db(self, db_name: str) -> None:
        """Connect to MongoDB client

        Parameters:
            db_name (`str`): Database name to log in. Will create new Database if not found.
        """
        # pylint: disable=attribute-defined-outside-init
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
        """Get collection from database.

        Parameters:
            name (`str`): Collection name to fetch
        """
        if name in self._list_collection:
            LOGGER.debug("Collection %s Found, fetching...", name)
        else:
            LOGGER.debug("Collection %s Not Found, Creating New Collection...", name)
        return self._db[name]

    async def _get_lang(self, chat_id) -> str:
        """Get user language setting."""
        col = self.get_collection("LANGUAGE")
        data = await col.find_one({'chat_id': chat_id})
        return data["language"] if data else 'en'  # default english

    async def text(self, chat_id: int, name: str, *args: object) -> str:
        """Parse the string with user language setting.

        Parameters:
            chat_id (`int`):
                Id of the sender(PM's) or chat_id to fetch the user language setting.

            name (`str`):
                String name to parse. The string is parsed from YAML documents.

            *args (`any`, *Optional*):
                One or more values that should be formatted and inserted in the string.
                The value should be in order (based on the placeholder on the YAML documents).
        """
        _lang = await self._get_lang(chat_id)

        if _lang in self.__language and name in self.__strings[_lang]:
            return (
                decode(
                    encode(
                        self.__strings[_lang][name],
                        'latin-1',
                        'backslashreplace',
                    ),
                    'unicode-escape',
                )
            ).format(*args)

        err = "NO LANGUAGE STRING FOR {} in {}".format(name, _lang)
        LOGGER.critical(err)
        return err + "\nPlease forward this to @userbotindo."
