""" Debugging purpose """
# Copyright (C) 2020 - 2023  UserbotIndo Team, <https://github.com/userbotindo.git>
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

import inspect
import io
import os
import re
import sys
import traceback
from datetime import datetime
from html import escape
from typing import Any, ClassVar, Optional, Tuple

import pyrogram
from meval import meval
from pyrogram.enums.chat_action import ChatAction

from anjani import command, filters, plugin, util


class Debug(plugin.Plugin):
    name: ClassVar[str] = "Debug"

    async def cmd_ping(self, ctx: command.Context) -> str:
        start = datetime.now()
        await ctx.respond("Calculating response time...")
        end = datetime.now()
        latency = (end - start).microseconds / 1000

        return f"Latency: {latency} ms"

    @command.filters(filters.dev_only)
    async def cmd_eval(self, ctx: command.Context) -> Optional[str]:
        code = ctx.input
        if not code:
            return "Give me code to evaluate."

        out_buf = io.StringIO()

        async def _eval() -> Tuple[str, Optional[str]]:
            # Message sending helper for convenience
            async def send(*args: Any, **kwargs: Any) -> pyrogram.types.Message:
                return await ctx.msg.reply(*args, **kwargs)

            # Print wrapper to capture output
            # We don't override sys.stdout to avoid interfering with other output
            def _print(*args: Any, **kwargs: Any) -> None:
                if "file" not in kwargs:
                    kwargs["file"] = out_buf

                return print(*args, **kwargs)

            eval_vars = {
                # Contextual info
                "self": self,
                "ctx": ctx,
                "bot": self.bot,
                "loop": self.bot.loop,
                "client": self.bot.client,
                "commands": self.bot.commands,
                "listeners": self.bot.listeners,
                "plugins": self.bot.plugins,
                "stdout": out_buf,
                # Convenience aliases
                "anjani": self.bot,
                "chat": ctx.chat,
                "context": ctx,
                "msg": ctx.msg,
                "message": ctx.msg,
                "db": self.bot.db,
                # Helper functions
                "send": send,
                "print": _print,
                # Built-in modules
                "inspect": inspect,
                "os": os,
                "re": re,
                "sys": sys,
                "traceback": traceback,
                # Third-party modules
                "pyrogram": pyrogram,
                # Custom modules
                "command": command,
                "plugin": plugin,
                "util": util,
            }

            try:
                return "", await meval(code, globals(), **eval_vars)
            except Exception as e:  # skipcq: PYL-W0703
                # Find first traceback frame involving the snippet
                first_snip_idx = -1
                tb = traceback.extract_tb(e.__traceback__)
                for i, frame in enumerate(tb):
                    if frame.filename == "<string>" or frame.filename.endswith("ast.py"):
                        first_snip_idx = i
                        break

                # Re-raise exception if it wasn't caused by the snippet
                if first_snip_idx == -1:
                    raise e

                # Return formatted stripped traceback
                stripped_tb = tb[first_snip_idx:]
                formatted_tb = util.error.format_exception(e, tb=stripped_tb)
                return "⚠️ Error executing snippet\n\n", formatted_tb

        before = util.time.usec()
        prefix, result = await _eval()
        after = util.time.usec()

        # Always write result if no output has been collected thus far
        if not out_buf.getvalue() or result is not None:
            print(result, file=out_buf)

        el_us = after - before
        el_str = util.time.format_duration_us(el_us)

        out = out_buf.getvalue()
        # Strip only ONE final newline to compensate for our message formatting
        if out.endswith("\n"):
            out = out[:-1]

        if len(out) > 4096:
            async with ctx.action(ChatAction.UPLOAD_DOCUMENT):
                with io.BytesIO(str.encode(out)) as out_file:
                    out_file.name = "eval.text"
                    await ctx.msg.reply_document(
                        document=out_file, caption=code, disable_notification=True
                    )

                return None

        await ctx.respond(
            f"""{prefix}<b>In:</b>
<pre language="python">{escape(code)}</pre>

<b>Out:</b>
<pre language="python">{escape(out)}</pre>

Time: {el_str}""",
            parse_mode=pyrogram.enums.parse_mode.ParseMode.HTML,
        )
