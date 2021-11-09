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

import re
from json import JSONDecodeError
from typing import Any, ClassVar, Optional

from aiohttp import ClientConnectorError, ClientSession, ContentTypeError
from aiopath import AsyncPath

from anjani import command, filters, plugin


class Paste:

    __token: Optional[str]

    def __init__(self, session: ClientSession, name: str, url: str):
        self.__session = session
        self.__name = name
        self.__url = url

        self.__token = None
        self.url_map = {
            "-h": "https://hastebin.com/",
            "-k": "https://katb.in/",
            "-s": "https://spaceb.in/",
            "hastebin": "https://hastebin.com/",
            "katbin": "https://katb.in/",
            "spacebin": "https://spaceb.in/",
        }

    async def __aenter__(self) -> "Paste":
        return self

    async def __aexit__(self, _: Any, __: Any, ___: Any) -> None:
        ...

    async def go(self, content: Any) -> str:
        if self.__name == "katbin":
            regex = re.compile(r'name="_csrf_token".+value="(.+)"')
            async with self.__session.get(self.__url) as r:
                if r.status == 200:
                    async for data in r.content.iter_any():
                        token = regex.search(data.decode("utf-8"))
                        if not token:
                            continue

                        self.__token = token.group(1)
                        break
            if self.__token:
                content["_csrf_token"] = self.__token

        async with self.__session.post(self.__url, data=content) as r:
            if self.__name == "katbin":
                return str(r.url)

            content_data = await r.json()
            url = self.url_map[self.__name]
            return (
                url + content_data["key"]
                if self.__name == "hastebin"
                else url + content_data["payload"]["id"]
            )


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

        data: Any
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

        uris = {
            "-h": "https://hastebin.com/documents",
            "-k": "https://katb.in/",
            "-s": "https://spaceb.in/api/v1/documents/",
            "hastebin": "https://hastebin.com/documents",
            "katbin": "https://katb.in/",
            "spacebin": "https://spaceb.in/api/v1/documents/",
        }
        try:
            uri = uris[service]
        except KeyError:
            return None
        else:
            hastebin = "hastebin" in uri
            katbin = "katb" in uri
            spacebin = "spaceb" in uri

        service = "hastebin" if hastebin else "katbin" if katbin else "spacebin"
        if katbin:
            data = {"paste[content]": data}

        if spacebin:
            data = {"content": data, "extension": "txt"}

        await ctx.respond(await self.text(chat.id, "wait-paste", service))

        try:
            async with Paste(self.bot.http, service, uri) as paste:
                return await self.text(
                    ctx.chat.id, "paste-succes", f"[{service}]({await paste.go(data)})"
                )
        except (JSONDecodeError, ContentTypeError, ClientConnectorError):
            return await self.text(ctx.chat.id, "fail-paste", service)

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
