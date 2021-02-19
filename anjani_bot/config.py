"""Module For AnjaniBot Configuration"""
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

from os import environ
from dotenv import load_dotenv


load_dotenv("config.env")


class Config:  # pylint: disable=too-few-public-methods
    """
    all available bot config from environ
    """

    # pyrogram required
    BOT_TOKEN = environ.get("BOT_TOKEN")
    API_ID = int(environ.get("API_ID"))
    API_HASH = environ.get("API_HASH")
    # Required
    DB_URI = environ.get("DB_URI")
    DOWNLOAD_PATH = environ.get("DOWNLOAD_PATH", "./downloads")
    # Staff  required
    OWNER_ID = int(environ.get("OWNER_ID", 0))
    # Recomended
    LOG_CHANNEL = int(environ.get("LOG_CHANNEL", 0))
    SPAMWATCH_API = environ.get("SW_API", None)
