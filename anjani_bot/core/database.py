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
from codecs import decode, encode
from typing import Any, List, Union, Optional, Dict

from yaml import full_load
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from motor.core import AgnosticCollection

from ..config import Config

LOGGER = logging.getLogger(__name__)


class DataBase:
    """Client Database on MongoDB"""
    _client: AsyncIOMotorClient
    _db: AsyncIOMotorDatabase
    _lang: AsyncIOMotorCollection
    _list_collection: List[str]

    __language: List[str] = ["en", "id"]
    __strings: Dict[str, str] = {}

    @property
    def language(self) -> list:
        """ Return list of bot suported languages """
        return self.__language

    @property
    def lang_col(self) -> AgnosticCollection:
        """ Return client language collection """
        return self._lang

    def _load_language(self):
        """Load bot language."""
        LOGGER.info("Loading language...")
        for i in self.__language:
            LOGGER.debug("Loading language: %s", i)
            with open(f"anjani_bot/core/language/{i}.yml", "r") as text:
                self.__strings[i] = full_load(text)
        LOGGER.info("Language %s loaded", self.__language)

    async def connect_db(self, db_name: str) -> None:
        """Connect to MongoDB client

        Parameters:
            db_name (`str`): Database name to log in. Will create new Database if not found.
        """
        LOGGER.info("Connecting to MongoDB...")
        self._client = AsyncIOMotorClient(Config.DB_URI, connect=False)
        if db_name in await self._client.list_database_names():
            LOGGER.info("Database found, Logged in to Database...")
        else:
            LOGGER.info("Database not found! Creating New Database...")
        self._db = self._client[db_name]
        self._list_collection = await self._db.list_collection_names()
        LOGGER.info("Database connected")
        self._lang = self.get_collection("LANGUAGE")

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

    async def get_lang(self, chat_id) -> str:
        """Get user language setting."""
        data = await self._lang.find_one({'chat_id': chat_id})
        return data["language"] if data else 'en'  # default english

    async def switch_lang(self, chat_id: Union[str, int], language: str) -> None:
        """ Change chat language setting. """
        await self._lang.update_one(
            {'chat_id': int(chat_id)},
            {"$set": {'language': language}},
            upsert=True,
        )

    async def text(
            self,
            chat_id: int,
            name: str,
            *args: Optional[Any],
            **kwargs: Optional[Any],
        ) -> str:
        """Parse the string with user language setting.

        Parameters:
            chat_id (`int`):
                Id of the sender(PM's) or chat_id to fetch the user language setting.

            name (`str`):
                String name to parse. The string is parsed from YAML documents.

            *args (`any`, *Optional*):
                One or more values that should be formatted and inserted in the string.
                The value should be in order based on the language string placeholder.

            **kwargs (`any`, *Optional*):
                One or more keyword values that should be formatted and inserted in the string.
                based on the keyword on the language strings.

            special parameters:
                noformat (`bool`, *Optional*):
                    If exist and True, the text returned will not be formated.
                    Default to False.

        """
        _lang = await self.get_lang(chat_id)
        noformat = bool(kwargs.get("noformat", False))

        if _lang in self.__language and name in self.__strings[_lang]:
            text = (
                decode(
                    encode(
                        self.__strings[_lang][name],
                        'latin-1',
                        'backslashreplace',
                    ),
                    'unicode-escape',
                )
            )
            return text if noformat else text.format(*args, **kwargs)
        err = "NO LANGUAGE STRING FOR {} in {}".format(name, _lang)
        LOGGER.warning(err)
        # try to send the english string first if not found
        try:
            text = (
                decode(
                    encode(
                        self.__strings["en"][name],
                        'latin-1',
                        'backslashreplace',
                    ),
                    'unicode-escape',
                )
            )
            return text if noformat else text.format(*args, **kwargs)
        except KeyError:
            return err + "\nPlease forward this to @userbotindo."
