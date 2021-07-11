from datetime import datetime
from typing import ClassVar

from anjani import command, plugin


class Debug(plugin.Plugin):
    name: ClassVar[str] = "Debug"

    async def cmd_ping(self, ctx: command.Context) -> str:
        start = datetime.now()
        await ctx.respond("Calculating response time...")
        end = datetime.now()
        latency = (end - start).microseconds / 1000

        return f"Latency: {latency} ms"