from typing import AsyncIterator

from aiopath import AsyncPath


async def getLangFile() -> AsyncIterator[AsyncPath]:
    async for language_file in AsyncPath("language").iterdir():
        if language_file.suffix == ".yml":
            yield language_file
