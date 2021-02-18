"""Bot thread manager"""
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
import os

from typing import Any, Callable, List
from concurrent.futures import ThreadPoolExecutor, Future
from functools import wraps, partial

WORKERS = os.cpu_count()
THREAD_POOL: ThreadPoolExecutor
TASKS: List[asyncio.Task] = []
LOGGER = logging.getLogger(__name__)


def submit_task(task: asyncio.coroutines.CoroWrapper, queue: asyncio.queues.Queue) -> None:
    """ submit task to task pool """
    queue.put_nowait(task)


def submit_thread(func: Callable[[Any], Any], *args: Any, **kwargs: Any) -> Future:
    """ submit thread to thread pool """
    return THREAD_POOL.submit(func, *args, **kwargs)


def run_in_thread(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """ run in a thread """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(THREAD_POOL, partial(func, *args, **kwargs))
    return wrapper


def start(queue: asyncio.queues.Queue):
    """ Start pooling"""
    global THREAD_POOL  # pylint: disable=global-statement
    THREAD_POOL = ThreadPoolExecutor(WORKERS)

    async def _task_worker():
        while True:
            coro = await queue.get()
            if coro is None:
                break
            await coro
    loop = asyncio.get_event_loop()
    for _ in range(WORKERS):
        TASKS.append(loop.create_task(_task_worker()))
    LOGGER.info("Started Pool : %s Workers", WORKERS)


async def stop(queue: asyncio.queues.Queue):
    """ stop pool """
    THREAD_POOL.shutdown()
    for _ in range(WORKERS):
        queue.put_nowait(None)
    for task in TASKS:
        try:
            await asyncio.wait_for(task, timeout=0.3)
        except asyncio.TimeoutError:
            task.cancel()
    TASKS.clear()
    LOGGER.info("Stopped Pool : %s Workers", WORKERS)
