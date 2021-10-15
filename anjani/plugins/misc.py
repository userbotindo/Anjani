"""miscellaneous bot commands"""
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

from json import JSONDecodeError
from typing import ClassVar, Optional

from aiohttp import ClientConnectorError
from aiopath import AsyncPath

from anjani import command, filters, plugin


class Misc(plugin.Plugin):
    name: ClassVar[str] = "Miscs"
    helpable: ClassVar[bool] = True

    async def cmd_id(self, ctx: command.Context) -> str:
        """Display ID's"""
        msg = ctx.msg.reply_to_message or ctx.msg
        out_str = f"👥 **Chat ID :** `{(msg.forward_from_chat or msg.chat).id}`\n"
        out_str += f"💬 **Message ID :** `{msg.forward_from_message_id or msg.message_id}`\n"
        if msg.from_user:
            out_str += f"🙋‍♂️ **From User ID :** `{msg.from_user.id}`\n"
        file = (
            msg.audio
            or msg.animation
            or msg.document
            or msg.photo
            or msg.sticker
            or msg.voice
            or msg.video_note
            or msg.video
        ) or None
        if file:
            out_str += f"📄 **Media Type :** `{file.__class__.__name__}`\n"
            out_str += f"📄 **File ID :** `{file.file_id}`"

        return out_str

    async def cmd_paste(self, ctx: command.Context, service: Optional[str] = None) -> Optional[str]:
        if not ctx.msg.reply_to_message:
            return None
        if not service:
            service = "hastebin"

        chat = ctx.chat
        reply_msg = ctx.msg.reply_to_message
        if reply_msg.document:
            file = AsyncPath(await reply_msg.download())
            data = await file.read_text()
            await file.unlink()
        elif reply_msg.text:
            data = reply_msg.text
        else:
            return None

        urls = {
            "-h": "https://hastebin.com/",
            "-k": "https://katb.in/",
            "hastebin": "https://hastebin.com/",
            "katbin": "https://katb.in/",
        }
        uris = {
            "-h": "https://hastebin.com/documents",
            "-k": "https://api.katb.in/api/paste",
            "hastebin": "https://hastebin.com/documents",
            "katbin": "https://api.katb.in/api/paste",
        }
        try:
            uri = uris[service]
        except KeyError:
            return None
        else:
            hastebin = "hastebin" in uri
            katbin = "katb" in uri

        if hastebin:
            service = "hastebin"
            json = {}
        else:
            service = "katbin"
            json = {"json": {"content": data}}

        await ctx.respond(await self.text(chat.id, "wait-paste", service))

        try:
            async with self.bot.http.post(uri, data=data if hastebin else None, **json) as resp:
                try:
                    result = await resp.json()
                except JSONDecodeError:
                    return await self.text(ctx.chat.id, "paste-fail", service)

                text = (
                    urls[service] + result["paste_id"] if katbin else urls[service] + result["key"]
                )
                return await self.text(ctx.chat.id, "paste-succes", f"[{service}]({text})")
        except ClientConnectorError:
            return await self.text(ctx.chat.id, "paste-fail", service)

    @command.filters(filters.private)
    async def cmd_source(self, ctx: command.Context) -> None:
        """Send the bot source code"""
        await ctx.respond(
            "[GitHub repo](https://github.com/userbotindo/Anjani)\n"
            + "[Support](https://t.me/userbotindo)",
            disable_web_page_preview=True,
        )

    @command.filters(filters.group)
    async def cmd_slap(self, ctx: command.Context) -> Optional[str]:
        """Slap member with neko slap."""
        text = ctx.input
        chat = ctx.msg.chat
        async with self.bot.http.get("https://www.nekos.life/api/v2/img/slap") as slap:
            if slap.status != 200:
                return await self.text(chat.id, "err-api-down")
            res = await slap.json()

        msg = ctx.msg.reply_to_message or ctx.msg
        await self.bot.client.send_animation(
            chat.id,
            res["url"],
            reply_to_message_id=msg.message_id,
            caption=text,
        )
        return None
