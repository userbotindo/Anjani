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
import os
import traceback
from codecs import decode, encode
from typing import Any, Dict, List, Optional, Union

from motor.core import AgnosticCollection
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.errors import OperationFailure
from yaml import full_load

from .base import Base  # pylint: disable=R0401

LOGGER = logging.getLogger(__name__)


class DataBase(Base):
    """Client Database on MongoDB"""

    __client__: AsyncIOMotorClient
    __db__: AsyncIOMotorDatabase
    __lang__: AsyncIOMotorCollection
    __language__: List[str]
    __list_collection__: List[str]
    __strings__: Dict[str, str]

    def __init__(self):
        self.__language__ = sorted(
            [os.path.splitext(filename)[0] for filename in os.listdir("./language")]
        )
        self.__strings__ = {}

        super().__init__()

    @property
    def language(self) -> list:
        """Return list of bot suported languages"""
        return self.__language__

    @property
    def lang_col(self) -> AgnosticCollection:
        """Return client language collection"""
        return self.__lang__

    def _load_language(self):
        """Load bot language."""
        LOGGER.info("Loading language...")
        for i in self.__language__:
            LOGGER.debug(f"Loading language: {i}")
            with open(f"./language/{i}.yml", "r") as text:
                self.__strings__[i] = full_load(text)
        LOGGER.debug(f"Language {self.__language__} loaded")

    async def connect_db(self, db_name: str) -> None:
        """Connect to MongoDB client

        Parameters:
            db_name (`str`): Database name to log in. Will create new Database if not found.
        """
        LOGGER.info("Connecting to MongoDB...")
        try:
            self.__client__ = AsyncIOMotorClient(self.get_config.db_uri, connect=False)
            if db_name in await self.__client__.list_database_names():
                LOGGER.debug("Database found, Logged in to Database...")
            else:
                LOGGER.debug("Database not found! Creating New Database...")
        except OperationFailure as err:
            traceback.print_exc()
            LOGGER.critical(f"DATABASE AUTHENTICATION FAILED\n{err}")
            await self.loop.stop()

        self.__db__ = self.__client__[db_name]
        self.__list_collection__ = await self.__db__.list_collection_names()
        LOGGER.info("Database connected")
        self.__lang__ = self.get_collection("LANGUAGE")

    async def disconnect_db(self) -> None:
        """Disconnect database client"""
        self.__client__.close()
        LOGGER.info("Disconnected from database")

    def get_collection(self, name: str) -> AgnosticCollection:
        """Get collection from database.

        Parameters:
            name (`str`): Collection name to fetch
        """
        if name in self.__list_collection__:
            LOGGER.debug(f"Collection {name} Found, fetching...")
        else:
            LOGGER.debug(f"Collection {name} Not Found, Creating New Collection...")
        return self.__db__[name]

    async def get_lang(self, chat_id) -> str:
        """Get user language setting."""
        data = await self.__lang__.find_one({"chat_id": chat_id})
        return data["language"] if data else "en"  # default english

    async def switch_lang(self, chat_id: Union[str, int], language: str) -> None:
        """Change chat language setting."""
        await self.__lang__.update_one(
            {"chat_id": int(chat_id)},
            {"$set": {"language": language}},
            upsert=True,
        )

    async def migrate_chat(self, old_chat: int, new_chat: int):
        """Run all migrate handler on every migrateable plugin"""
        LOGGER.debug(f"Migrating chat from {old_chat} to {new_chat}")
        for plugin in list(self.plugins.values()):
            if hasattr(plugin, "__migrate__"):
                await plugin.__migrate__(old_chat, new_chat)

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
        lang = await self.get_lang(chat_id)
        noformat = bool(kwargs.get("noformat", False))

        if lang in self.__language__ and name in self.__strings__[lang]:
            text = decode(
                encode(
                    self.__strings__[lang][name],
                    "latin-1",
                    "backslashreplace",
                ),
                "unicode-escape",
            )
            return text if noformat else text.format(*args, **kwargs)
        err = "NO LANGUAGE STRING FOR {} in {}".format(name, lang)
        LOGGER.warning(err)
        # try to send the english string first if not found
        try:
            text = decode(
                encode(
                    self.__strings__["en"][name],
                    "latin-1",
                    "backslashreplace",
                ),
                "unicode-escape",
            )
            return text if noformat else text.format(*args, **kwargs)
        except KeyError:
            return err + "\nPlease forward this to @userbotindo."

    async def backup_plugin_data(
        self, chat_id: int, data: Optional[Dict] = None
    ) -> Union[Dict, None]:
        """Backup chat data

        Parameters:
            chat_id (`int`):
                Id of the sender(PM's) or chat_id to fetch the user language setting.
            data (`dict`, *Optional*):
                Data to restore. Only pass this if you want to restore.

        Returns:
            dict of backup if no data passed, otherwise None.
        """
        if not isinstance(data, (type(None), dict)):
            raise BackupError("Data must be a dict or Nonetype " f"not {data.__class__.__name__}")

        LOGGER.debug("{} chat data from {}", "Importing" if data else "Exporting", chat_id)
        result = {"chat_id": chat_id}
        for plugin in list(self.plugins.values()):
            if hasattr(plugin, "__backup__"):
                if not data:
                    LOGGER.debug(f"Backing up {plugin.name} data")
                    plugin_data = await plugin.__backup__(chat_id)
                    if not isinstance(plugin_data, (type(None), dict)):
                        raise BackupError(
                            f"Unexpected return value type from `{plugin.name}` plugin: "
                            "expecting a dict or NoneType, "
                            f"got {plugin_data.__class__.__name__}"
                        )
                    if not plugin_data:  # skip plugin if no data
                        continue
                    result.update({plugin.name: plugin_data})
                else:
                    LOGGER.debug(f"restoring {plugin.name} data")
                    await plugin.__backup__(chat_id, data)
        return result if not data else None


class BackupError(Exception):
    """Unexpected backup data type"""
