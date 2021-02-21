"""AnjaniBot Configuration"""
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

import os

from dotenv import load_dotenv
from typing import Union


class BotConfig:
    """
    Bot configuration
    """

    def __init__(self) -> Union[str, int]:
        if os.path.isfile("config.env"):
            load_dotenv("config.env")

        # Core config
        self.API_ID = int(os.environ.get("API_ID", 0))
        self.API_HASH = os.environ.get("API_HASH")
        self.BOT_TOKEN = os.environ.get("BOT_TOKEN")
        self.DB_URI = os.environ.get("DB_URI")

        # Optional
        self.DOWNLOAD_PATH = os.environ.get("DOWNLOAD_PATH", "./downloads")
        self.LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0))
        self.SPAMWATCH_API = os.environ.get("SW_API", None)

        # Manager required
        self.OWNER_ID = int(os.environ.get("OWNER_ID", 0))
