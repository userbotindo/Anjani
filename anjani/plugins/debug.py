from datetime import datetime
from typing import ClassVar

from pyrogram import filters
import pyrogram

from anjani import command, listener, plugin


class Debug(plugin.Plugin):
    name: ClassVar[str] = "Debug"

    @command.filters(filters.chat(-1001554717157))
    async def cmd_ping(self, ctx: command.Context) -> str:
        start = datetime.now()
        await ctx.respond("Calculating response time...")
        end = datetime.now()
        latency = (end - start).microseconds / 1000

        return f"Latency: {latency} ms"