import asyncio
from typing import List

from aiopath import AsyncPath


async def getLangFile() -> List[AsyncPath]:
    return sorted([AsyncPath(langFile)
                   async for langFile in AsyncPath("language").iterdir()
                   if langFile.name.endswith(".yml")])


languages = asyncio.get_event_loop().run_until_complete(getLangFile())