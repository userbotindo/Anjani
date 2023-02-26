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
from typing import Any, ClassVar, MutableMapping

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

try:
    import userbotindo

    _run_canonical = True
    del userbotindo
except ImportError:
    _run_canonical = False


from anjani import command, filters, listener, plugin, util


class Canonical(plugin.Plugin):
    """Helper Plugin
    This plugin is only available for @dAnjani_bot
    to comunicate with https://userbotindo.com
    """

    name: ClassVar[str] = "Canonical"
    disabled: ClassVar[bool] = not _run_canonical

    # Private
    __task: asyncio.Task[None]
    _mt: MutableMapping[MessageMediaType, str] = {
        MessageMediaType.STICKER: "s",
        MessageMediaType.PHOTO: "p",
        MessageMediaType.DOCUMENT: "f",
        MessageMediaType.VIDEO: "v",
    }

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("TEST")
        self.db_analytics = self.bot.db.get_collection("ANALYTICS")
        self.chats_db = self.bot.db.get_collection("CHATS")

    async def on_start(self, _: int) -> None:
        self.log.debug("Starting watch streams")
        self.__task = self.bot.loop.create_task(self.watch_streams())

    async def on_stop(self) -> None:
        self.log.debug("Stopping watch streams")
        self.__task.cancel()

    def get_type(self, message: Message) -> str:
        return self._mt.get(message.media, "t") if message.media else "t"

    async def save_message_type(self, message: Message) -> None:
        today = util.time.sec()
        timestamp = today - (today % 86400)  # truncate to day
        await self.db_analytics.update_one(
            {"key": 2},
            {"$inc": {f"data.{str(timestamp)}.{self.get_type(message)}": 1}},
            upsert=True,
        )

    @command.filters(filters.admin_only & filters.group)
    async def cmd_r(self, ctx: command.Context) -> None:
        """Refresh chat data"""
        admins = []
        async for member in self.bot.client.get_chat_members(
            ctx.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
        ):  # type: ignore
            if not member.user.is_bot and member.privileges.can_manage_chat:
                admins.append(member.user.id)

        await self.chats_db.update_one(
            {"chat_id": ctx.chat.id}, {"$set": {"admins": admins}}, upsert=True
        )
        await ctx.respond("Done", delete_after=5)

    @listener.priority(65)
    async def on_message(self, message: Message) -> None:
        if message.outgoing:
            return

        # Analytics
        self.bot.loop.create_task(self.save_message_type(message))

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
        if not self.bot.config["login_url"]:
            return

        await ctx.respond(
            "Click this button to login to Anjani Dashboard",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Login",
                            login_url=LoginUrl(
                                url=self.bot.config["login_url"],
                                forward_text="Login to https://userbotindo.com",
                                request_write_access="True",
                            ),
                        )
                    ]
                ]
            ),
        )
