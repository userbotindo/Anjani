from datetime import datetime
from typing import ClassVar

from pyrogram import filters

from anjani import command, listener, plugin


class Debug(plugin.Plugin):
    name: ClassVar[str] = "Debug"

    @command.filters(filters.private | filters.chat(-587989142))
    async def cmd_ping(self, ctx: command.Context) -> str:
        start = datetime.now()
        await ctx.respond("Calculating response time...")
        end = datetime.now()
        latency = (end - start).microseconds / 1000

        return f"Latency: {latency} ms"

    @listener.filters(filters.regex(r"^.ping") & filters.private)
    async def on_message(self, message) -> None:
        self.log.info(message.matches)
    
    @listener.filters(filters.regex(r"^/ping"))
    async def on_inline_query(self, query) -> None:
        self.log.info(query.matches)
    
    async def on_chat_action(self, chat) -> None:
        self.log.info(chat.new_chat_members)
        self.log.info(chat.left_chat_member)
