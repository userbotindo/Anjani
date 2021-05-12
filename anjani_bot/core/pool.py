"""Bot thread manager"""
# Copyright https://github.com/UsergeTeam/Userge/blob/alpha/userge/core/ext/pool.py
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

import asyncio
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial, wraps
from typing import Any, Callable

from motor.frameworks.asyncio import _EXECUTOR as exe

LOGGER = logging.getLogger(__name__)


def submit_thread(func: Callable[[Any], Any], *args: Any, **kwargs: Any) -> Future:
    """submit thread to thread pool"""
    return exe.submit(func, *args, **kwargs)


def run_in_thread(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """run in a thread"""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(exe, partial(func, *args, **kwargs))

    return wrapper


# pylint: disable=W0212
def start() -> ThreadPoolExecutor:
    """start pool"""
    LOGGER.info(f"Started Pool : {exe._max_workers} Workers")
    return exe


def stop():
    """stop pool"""
    exe.shutdown()
    LOGGER.info(f"Stopped Pool : {exe._max_workers} Workers")
