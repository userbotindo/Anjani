"""Bot thread manager"""
import asyncio
import logging
import os

from typing import Any, Callable, List
from concurrent.futures import ThreadPoolExecutor, Future
from functools import wraps, partial

WORKERS = os.cpu_count()
THREAD_POOL: ThreadPoolExecutor
ASYNC_Q = asyncio.Queue()
TASKS: List[asyncio.Task] = []
LOGGER = logging.getLogger(__name__)


def submit_task(task: asyncio.coroutines.CoroWrapper) -> None:
    """ submit task to task pool """
    ASYNC_Q.put_nowait(task)


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


def start():
    """ Start pooling"""
    global THREAD_POOL  # pylint: disable=global-statement
    THREAD_POOL = ThreadPoolExecutor(WORKERS)

    async def _task_worker():
        while True:
            coro = await ASYNC_Q.get()
            if coro is None:
                break
            await coro
    loop = asyncio.get_event_loop()
    for _ in range(WORKERS):
        TASKS.append(loop.create_task(_task_worker()))
    LOGGER.info("Started Pool : %s Workers", WORKERS)


async def stop():
    """ stop pool """
    THREAD_POOL.shutdown()
    for _ in range(WORKERS):
        ASYNC_Q.put_nowait(None)
    for task in TASKS:
        try:
            await asyncio.wait_for(task, timeout=0.3)
        except asyncio.TimeoutError:
            task.cancel()
    TASKS.clear()
    LOGGER.info("Stopped Pool : %s Workers", WORKERS)
