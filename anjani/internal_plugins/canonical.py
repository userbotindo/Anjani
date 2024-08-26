""" Canonical plugin for @dAnjani_bot """

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

import asyncio
import logging
from base64 import b64encode
from typing import Any, ClassVar, MutableMapping

from aiohttp import web
from aiopath import AsyncPath
from prometheus_client import REGISTRY, generate_latest
from pymongo.errors import PyMongoError
from pyrogram.enums.chat_member_status import ChatMemberStatus
from pyrogram.enums.chat_members_filter import ChatMembersFilter
from pyrogram.enums.message_media_type import MessageMediaType
from pyrogram.types import (
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LoginUrl,
    Message,
)

from anjani import command, filters, listener, plugin
from anjani.core.metrics import MessageStat

# metrics endpoint filter
logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


async def metrics_handler(_: web.Request):
    metrics = generate_latest(REGISTRY)
    return web.Response(body=metrics, content_type="text/plain")


class Canonical(plugin.Plugin):
    """Helper Plugin
    This plugin is only available for @dAnjani_bot
    to comunicate with https://userbotindo.com
    """

    name: ClassVar[str] = "Canonical"

    # Private
    _web_runner: web.AppRunner
    _web_site: web.TCPSite
    _api_key: str
    _internal_api_url: str

    __web_task: asyncio.Task[None]
    __task: asyncio.Task[None]
    _mt: MutableMapping[MessageMediaType, str] = {
        MessageMediaType.STICKER: "sticker",
        MessageMediaType.PHOTO: "photo",
        MessageMediaType.DOCUMENT: "file",
        MessageMediaType.VIDEO: "video",
    }

    async def on_load(self):
        self._api_key = self.bot.config.USERBOTINDO_API_KEY
        self._internal_api_url = self.bot.config.USERBOTINDO_API_URL

        if not self._api_key or not self._internal_api_url:
            self.bot.unload_plugin(self)
            return

        self.db = self.bot.db.get_collection("TEST")
        self.chats_db = self.bot.db.get_collection("CHATS")
        await self._setup_web_app()

    async def _setup_web_app(self):
        app = web.Application()
        app.add_routes([web.get("/metrics", metrics_handler)])
        self._web_runner = web.AppRunner(app)
        await self._web_runner.setup()
        self._web_site = web.TCPSite(self._web_runner, "0.0.0.0", 9090)
        await self._web_site.start()

    async def stop_aiohttp_server(self):
        if self._web_site:
            await self._web_site.stop()
        if self._web_runner:
            await self._web_runner.cleanup()

    async def on_start(self, _: int) -> None:
        self.log.debug("Starting watch streams")
        self.__task = self.bot.loop.create_task(self.watch_streams())
        self.__web_task = self.bot.loop.create_task(self._setup_web_app())

        async def _web_shutdown(task: asyncio.Task[None]) -> None:
            if task.cancelled():
                await self.stop_aiohttp_server()

        def shutdown_wrapper(task):
            asyncio.create_task(_web_shutdown(task))

        self.__web_task.add_done_callback(shutdown_wrapper)

    async def on_stop(self) -> None:
        self.log.debug("Stopping watch streams")
        self.__task.cancel()
        self.log.debug("Shutting down web app")
        self.__web_task.cancel()

    def get_type(self, message: Message) -> str:
        if message.command:
            return "command"
        return self._mt.get(message.media, "text") if message.media else "text"

    @command.filters(filters.admin_only & filters.group)
    async def cmd_r(self, ctx: command.Context) -> None:
        """Refresh chat data"""
        admins = []
        async for member in self.bot.client.get_chat_members(
            ctx.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
        ):  # type: ignore
            if not member.user.is_bot and member.privileges.can_manage_chat:
                admins.append(member.user.id)

        photo = None
        if ctx.chat.photo:
            file = await self.bot.client.download_media(ctx.chat.photo.small_file_id)
            if file and isinstance(file, str):
                file = AsyncPath(file)
                result = await file.read_bytes()
                photo = b64encode(result).decode("utf-8")
                await file.unlink()
            if file and isinstance(file, bytes):
                photo = b64encode(file).decode("utf-8")

        await self.chats_db.update_one(
            {"chat_id": ctx.chat.id}, {"$set": {"admins": admins, "photo": photo}}, upsert=True
        )
        await ctx.respond("Done", delete_after=5)

    @listener.priority(65)
    async def on_message(self, message: Message) -> None:
        """Message metric analytics"""
        if message.outgoing:
            return

        MessageStat.labels(self.get_type(message)).inc()

    async def on_chat_action(self, message: Message) -> None:
        """Delete admins data from chats"""
        if message.new_chat_members:
            return

        chat = message.chat
        user = message.left_chat_member
        if user.id == self.bot.uid:
            await asyncio.gather(
                self.chats_db.update_one({"chat_id": chat.id}, {"$set": {"admins": []}}),
            )

    async def on_chat_member_update(self, update: ChatMemberUpdated) -> None:
        old_data = update.old_chat_member
        new_data = update.new_chat_member

        if not old_data or not new_data:  # Rare case
            return

        if old_data.status == new_data.status:
            return

        if new_data.status not in {
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        }:
            await self.chats_db.update_one(
                {"chat_id": update.chat.id}, {"$pull": {"admins": new_data.user.id}}
            )
        elif (
            new_data.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}
            and new_data.privileges
            and new_data.privileges.can_manage_chat
        ):  # type: ignore
            await self.chats_db.update_one(
                {"chat_id": update.chat.id},
                {"$addToSet": {"admins": new_data.user.id}},
                upsert=True,
            )

    async def watch_streams(self) -> None:
        try:
            async with self.db.watch([{"$match": {"operationType": "insert"}}]) as stream:
                async for change in stream:
                    await self.dispatch_change(change["fullDocument"])
        except PyMongoError as e:
            self.log.error("Error", exc_info=e)

    async def dispatch_change(self, doc: MutableMapping[str, Any]) -> None:
        chat_id = int(doc["_id"])
        message = doc["message"]
        pin = doc.get("pin", False)
        disable_preview = doc.get("disable_preview", False)

        try:
            msg = await self.bot.client.send_message(
                chat_id=chat_id,
                text=message,
                disable_web_page_preview=disable_preview,
            )
            if pin:
                await self.bot.client.pin_chat_message(msg.chat.id, msg.id)
        except Exception as e:  # skipcq: PYL-W0703
            self.log.error(f"Error sending message to {chat_id}", exc_info=e)
        finally:
            await self.db.delete_one({"_id": chat_id})

    @command.filters(filters.private)
    async def cmd_login(self, ctx: command.Context):
        """Login to https://userbotindo.com"""
        if not self.bot.config.LOGIN_URL:
            return

        await ctx.respond(
            "Click this button to login to Anjani Dashboard",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Login",
                            login_url=LoginUrl(
                                url=self.bot.config.LOGIN_URL,
                                forward_text="Login to https://userbotindo.com",
                                request_write_access="True",
                            ),
                        )
                    ]
                ]
            ),
        )

    async def _create_token(self, ctx: command.Context, reference: str):
        async with self.bot.http.post(
            self._internal_api_url + "/admin/keys",
            headers={"x-api-key": self._api_key},
            json={"reference": reference},
        ) as resp:
            if resp.status != 201:
                self.log.error("Failed to create internal token", resp)
                return "Failed to create token"

            res = await resp.json()
            return f"Your new UserbotIndo API Key is:\n\n`{res['data']['key']}`"

    @command.filters(filters.private)
    async def cmd_token(self, ctx: command.Context):
        """Get token for userbotindo services"""
        reference = "tg-user@" + str(ctx.author.id)
        async with self.bot.http.get(
            self._internal_api_url + f"/admin/keys/{reference}",
            headers={"x-api-key": self._api_key},
        ) as resp:
            if resp.status == 404:
                return await self._create_token(ctx, reference)

            if resp.status != 200:
                self.log.error("Failed to get internal token", resp)
                return "Failed to get token"

            res = await resp.json()
            return f"Your current UserbotIndo API Key is:\n\n`{res['data']['key']}`"
