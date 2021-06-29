"""Bot tools"""
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

import time
from random import choice
from typing import Union
from uuid import uuid4

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError

__all__ = [
    "extract_time",
    "format_integer",
    "get_readable_time",
    "paste",
    "PasteBin",
    "rand_array",
    "rand_key",
]


class PasteBin:
    """Class that representate a paste result"""

    DOGBIN_URL = "https://del.dog/"
    HASTEBIN_URL = "https://hastebin.com/"
    NEKOBIN_URL = "https://nekobin.com/"
    _dkey = None
    _hkey = None
    _nkey = None
    retry = None

    def __init__(self, http: ClientSession, data: str = None):
        if not isinstance(http, ClientSession):
            raise AttributeError(
                "Invalid http instance, recieved "
                f'"{http.__class__.__name__}" expecting "aiohttp.client.ClientSession"'
            )
        self.http = http
        self.data = data
        self.retries = 3

    def __bool__(self):
        return bool(self._dkey or self._nkey or self._hkey)

    async def __call__(self, service="dogbin"):
        if service == "dogbin":
            await self._post_dogbin()
        elif service == "nekobin":
            await self._post_nekobin()
        elif service == "hastebin":
            await self._post_hastebin()
        else:
            raise KeyError(f"Unknown service input: {service}")

    async def _post_dogbin(self):
        if self._dkey:
            return
        try:
            async with self.http.post(
                self.DOGBIN_URL + "documents", data=self.data.encode("utf-8")
            ) as req:
                if req.status == 200:
                    res = await req.json()
                    self._dkey = res["key"]
                else:
                    self.retry = "nekobin"
        except ClientConnectorError:
            self.retry = "nekobin"

    async def _post_nekobin(self):
        if self._nkey:
            return
        try:
            async with self.http.post(
                self.NEKOBIN_URL + "api/documents", json={"content": self.data}
            ) as req:
                if req.status == 201:
                    res = await req.json()
                    self._nkey = res["result"]["key"]
                else:
                    self.retry = "hastebin"
        except ClientConnectorError:
            self.retry = "hastebin"

    async def _post_hastebin(self):
        if self._hkey:
            return
        try:
            async with self.http.post(
                self.HASTEBIN_URL + "documents", data=self.data.encode("utf-8")
            ) as req:
                if req.status == 200:
                    res = await req.json()
                    self._hkey = res["key"]
                else:
                    self.retry = "dogbin"
        except ClientConnectorError:
            self.retry = "dogbin"

    async def post(self, serv: str = "dogbin"):
        """Post the initialized data to the pastebin service."""
        if self.retries == 0:
            return

        await self.__call__(serv)

        if self.retry:
            self.retries -= 1
            await self.post(self.retry)
            self.retry = None

    @property
    def link(self) -> str:
        """Return the view link"""
        if self._dkey:
            return self.DOGBIN_URL + self._dkey
        if self._nkey:
            return self.NEKOBIN_URL + self._nkey
        if self._hkey:
            return self.HASTEBIN_URL + self._hkey
        return False

    @property
    def raw_link(self) -> str:
        """Return the view raw link"""
        if self._dkey:
            return self.DOGBIN_URL + "raw/" + self._dkey
        if self._nkey:
            return self.NEKOBIN_URL + "raw/" + self._nkey
        if self._hkey:
            return self.HASTEBIN_URL + "raw/" + self._hkey
        return False


async def paste(http: ClientSession, data: str) -> PasteBin:
    """Paste to a pastebin service"""
    pasted = PasteBin(http, data)
    await pasted.post()
    return pasted


def get_readable_time(seconds: int) -> str:
    """get human readable time from seconds."""
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    for count in range(1, 4):
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for index in enumerate(time_list):
        time_list[index[0]] = str(time_list[index[0]]) + time_suffix_list[index[0]]
    if len(time_list) == 4:
        up_time += time_list.pop() + ", "

    time_list.reverse()
    up_time += ":".join(time_list)

    return up_time


async def extract_time(time_text) -> Union[int, bool]:
    """Extract time from time flags"""
    if any(time_text.endswith(unit) for unit in ("m", "h", "d")):
        unit = time_text[-1]
        time_num = time_text[:-1]
        if not time_num.isdigit():
            return False

        if unit == "m":
            bantime = int(time.time() + int(time_num) * 60)
        elif unit == "h":
            bantime = int(time.time() + int(time_num) * 60 * 60)
        elif unit == "d":
            bantime = int(time.time() + int(time_num) * 24 * 60 * 60)
        return bantime
    return False


def format_integer(number: int, separator: str = ".") -> str:
    """make an integer easy to read"""
    return "{:,}".format(number).replace(",", separator)


def rand_array(array: list):
    """pick an item randomly from list"""
    return choice(array)


def rand_key():
    """generates a random key"""
    return str(uuid4())
