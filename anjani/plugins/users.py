"""User data management"""
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
import re
from hashlib import md5
from html import escape
from time import time
from typing import Any, ClassVar, List, Mapping, MutableMapping, Optional, Union

from pyrogram.enums.chat_action import ChatAction
from pyrogram.enums.chat_type import ChatType
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.errors import BadRequest, ChannelInvalid, ChannelPrivate, PeerIdInvalid
from pyrogram.types import CallbackQuery, Chat, ChatPreview, Message, User

from anjani import command, listener, plugin, util

try:
    from userbotindo import get_trust
except ImportError:
    from anjani.util.misc import do_nothing as get_trust


class Users(plugin.Plugin):
    name: ClassVar[str] = "Users"

    chats_db: util.db.AsyncCollection
    users_db: util.db.AsyncCollection
    predict_loaded: bool

    async def on_load(self) -> None:
        self.chats_db = self.bot.db.get_collection("CHATS")
        self.users_db = self.bot.db.get_collection("USERS")
        self.predict_loaded = "SpamPredict" in self.bot.plugins

    def hash_id(self, id: int) -> str:
        # skipcq: PTC-W1003
        return md5((str(id) + self.bot.user.username).encode()).hexdigest()  # skipcq: BAN-B324

    async def build_channel_task(self, channel: Chat) -> asyncio.Task[Any]:
        async def _do_nothing() -> None:
            return

        if channel.type == ChatType.CHANNEL:
            data = await self.chats_db.find_one({"chat_id": channel.id})
            content = {"chat_name": channel.title, "type": "channel"}
            if not data or "hash" not in data:
                content["hash"] = self.hash_id(channel.id)
            return self.bot.loop.create_task(
                self.chats_db.update_one({"chat_id": channel.id}, {"$set": content}, upsert=True)
            )

        return self.bot.loop.create_task(_do_nothing())

    async def build_user_task(self, user: User) -> asyncio.Task:
        data = await self.users_db.find_one({"_id": user.id})
        content: MutableMapping[str, Any] = {"username": user.username, "last_seen": int(time())}
        if not data or "hash" not in data:
            content["hash"] = self.hash_id(user.id)
        if not data or "chats" not in data:
            content["chats"] = []
        return self.bot.loop.create_task(
            self.users_db.update_one({"_id": user.id}, {"$set": content}, upsert=True)
        )

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await asyncio.gather(
            self.users_db.update_many({"chats": old_chat}, {"$push": {"chats": new_chat}}),
            self.users_db.update_many({"chats": old_chat}, {"$pull": {"chats": old_chat}}),
            self.chats_db.update_one({"chat_id": old_chat}, {"$set": {"chat_id": new_chat}}),
        )

    async def on_chat_action(self, message: Message) -> None:
        """Delete user data from chats"""
        if message.new_chat_members:
            return

        chat = message.chat
        user = message.left_chat_member
        if user.id == self.bot.uid:
            await asyncio.gather(
                self.chats_db.update_one({"chat_id": chat.id}, {"$set": {"member": []}}),
                self.users_db.update_many({"chats": chat.id}, {"$pull": {"chats": chat.id}}),
            )
        else:
            await asyncio.gather(
                self.users_db.update_one({"_id": user.id}, {"$pull": {"chats": chat.id}}),
                self.chats_db.update_one({"chat_id": chat.id}, {"$pull": {"member": user.id}}),
            )

    async def on_callback_query(self, query: CallbackQuery) -> None:
        """Hanle user that sent a callback query"""
        user = query.from_user
        set_content = {"username": user.username, "name": user.first_name}
        user_data = await self.users_db.find_one({"_id": user.id})

        if self.predict_loaded and (not user_data or "hash" not in user_data):
            set_content["hash"] = self.hash_id(user.id)

        await self.users_db.update_one({"_id": user.id}, {"$set": set_content})

    @listener.priority(50)
    async def on_message(self, message: Message) -> None:
        """Incoming message handler."""
        if message.outgoing:
            return

        chat = message.chat
        user = message.from_user

        if not user or not chat:  # sanity check for service
            return

        tasks = []
        set_content = {"username": user.username, "name": user.first_name, "last_seen": int(time())}
        user_data = await self.users_db.find_one({"_id": user.id})

        if chat.type == ChatType.PRIVATE:
            if self.predict_loaded:
                if ch := message.forward_from_chat:
                    tasks.append(await self.build_channel_task(ch))
                if not user_data or "hash" not in user_data:
                    set_content["hash"] = self.hash_id(user.id)
                if usr := message.forward_from:
                    tasks.append(await self.build_user_task(usr))

            await asyncio.gather(
                self.users_db.update_one({"_id": user.id}, {"$set": set_content}), *tasks
            )
            return

        chat_data = await self.chats_db.find_one({"chat_id": chat.id})
        chat_update = {
            "$set": {
                "chat_name": chat.title,
                "type": chat.type.name.lower(),
                "last_update": int(time()),
            },
            "$addToSet": {"member": user.id},
        }
        if self.predict_loaded:
            if not user_data or "hash" not in user_data:
                set_content["hash"] = self.hash_id(user.id)
            if not chat_data or "hash" not in chat_data:
                chat_update["$set"]["hash"] = self.hash_id(chat.id)
            update = {
                "$set": set_content,
                "$setOnInsert": {"reputation": 0},
                "$addToSet": {"chats": chat.id},
            }
            if ch := message.forward_from_chat:
                tasks.append(await self.build_channel_task(ch))
            if usr := message.forward_from:
                tasks.append(await self.build_user_task(usr))
        else:
            update = {"$set": set_content, "$addToSet": {"chats": chat.id}}

        await asyncio.gather(
            self.users_db.update_one({"_id": user.id}, update, upsert=True),
            self.chats_db.update_one({"chat_id": chat.id}, chat_update, upsert=True),
            *tasks,
        )

    async def _user_info(self, ctx: command.Context, user: User) -> None:
        """User Info"""
        text = f"<b>{'Bot' if user.is_bot else 'User'} Info</b>\n\n"
        text += f"<b>ID:</b> <code>{user.id}</code>\n"
        text += f"<b>DC ID: </b><code>{user.dc_id if user.dc_id else 'N/A'}</code>\n"
        text += f"<b>First Name: </b>{escape(user.first_name) if user.first_name else ''}\n"
        if user.last_name:
            text += f"<b>Last Name: </b><code>{escape(user.last_name)}</code>\n"

        if user.username:
            text += f"<b>Username: </b>@{user.username}\n"

        self.bot.client.parse_mode = ParseMode.HTML
        text += f"<b>Permanent user link: </b>{user.mention}\n"
        self.bot.client.parse_mode = ParseMode.MARKDOWN  # telegram_bot.py#L108

        text += (
            "<b>Number of profile pics: </b>"
            f"<code>{await self.bot.client.get_chat_photos_count(user.id)}</code>\n"
        )
        if user.status:
            text += f"<b>Last seen: </b> <code>{user.status.value}</code>\n"

        if user.id in self.bot.staff:
            text += "\nThis person is one of my <b>Staff</b>!\n"
        elif user.is_self:
            text += "\nI've seen them in every chats... wait it's me!!\nWow you're stalking me? 😂"

        if user.is_scam:
            text += "<b>\n⚠️Warning this user is flagged as a scammer by Telegram⚠️</b>\n"

        user_db = await self.users_db.find_one({"_id": user.id})
        if user_db and self.predict_loaded:
            if user_db.get("spam", False):
                text += "<b>\n⚠️Warning I flag this user as a spammer⚠️</b>\n"

            text += f"\n<b>Identifier:</b> <code>{user_db.get('hash', 'unknown')}</code>"
            text += f"\n<b>Reputation:</b> <code>{user_db.get('reputation', 0)}</code>"
            trust = get_trust(user_db.get("pred_sample", []))
            if trust:
                text += f"\n<b>Trust:</b> <code>{trust:.2f}</code>"
            else:
                text += "\n<b>Trust:</b> <code>N/A</code>"

        if user.photo:
            async with ctx.action(ChatAction.UPLOAD_PHOTO):
                file = await self.bot.client.download_media(user.photo.big_file_id)
                if not file:
                    await ctx.respond(text, parse_mode=ParseMode.HTML)
                    return

                try:
                    await self.bot.client.send_photo(
                        ctx.chat.id,
                        file,
                        text,
                        reply_to_message_id=ctx.message.id,
                        parse_mode=ParseMode.HTML,
                    )
                except ValueError:  # Wierd case where the photo id exist but have 0 bytes
                    await ctx.respond(text, parse_mode=ParseMode.HTML)
            return

        await ctx.respond(text, parse_mode=ParseMode.HTML)

    async def _old_user_info(self, data: Mapping[str, Any]) -> str:
        text = "<b>Old User Info</b>\n\n"
        text += f"<b>ID</b>: <code>{data['_id']}</code>\n"
        if data.get("name"):
            text += f"<b>Name</b>: {escape(data['name'])}\n"
        if data.get("username"):
            text += f"<b>Username</b>: @{data['username']}\n"
        if self.predict_loaded:
            text += f"\n<b>Identifier</b>: <code>{data.get('hash', 'unknown')}</code>"
            text += f"\n<b>Reputation</b>: <code>{data.get('reputation', 0)}</code>"
        text += f"\nI've seen them on {len(data.get('chats', []))} chats."
        return text

    async def _chat_info(self, ctx: command.Context, chat: Union[Chat, ChatPreview]) -> None:
        """Chat Info"""
        text = "<b>Chat Info</b>\n\n"
        if isinstance(chat, ChatPreview):
            text += f"<b>Chat Type:</b> <code>{chat.type}</code>\n"
            text += f"<b>Title:</b> <code>{escape(chat.title)}</code>\n"
            text += f"<b>Member Count:</b> <code>{chat.members_count}</code>\n"
        else:
            text += f"<b>ID:</b> <code>{chat.id}</code>\n"
            if chat.dc_id:
                text += f"<b>DC ID:</b> <code>{chat.dc_id}</code>\n"
            text += f"<b>Chat Type:</b> <code>{chat.type.__dict__['_name_']}</code>\n"
            text += f"<b>Title:</b> <code>{chat.title}</code>\n"
            if chat.username:
                text += f"<b>Chat Username:</b> @{chat.username}\n"
            text += f"<b>Member Count:</b> <code>{chat.members_count}</code>\n"
            if chat.linked_chat:
                text += f"<b>Linked Chat:</b> <code>{chat.linked_chat.title}</code>\n"

            if self.predict_loaded:
                chat_data = await self.chats_db.find_one({"chat_id": chat.id})
                if chat_data:
                    text += f"<b>Identifier:</b> <code>{chat_data.get('hash', 'unknown')}</code>\n"

        if chat.photo:
            async with ctx.action(ChatAction.UPLOAD_PHOTO):
                file = await self.bot.client.download_media(chat.photo.big_file_id)  # type: ignore
                if not file:
                    await ctx.respond(text, parse_mode=ParseMode.HTML)
                    return

                await self.bot.client.send_photo(
                    ctx.chat.id,
                    file,
                    text,
                    reply_to_message_id=ctx.message.id,
                    parse_mode=ParseMode.HTML,
                )
            return

        await ctx.respond(text, parse_mode=ParseMode.HTML)
        return

    async def _old_chat_info(self, data: Mapping[str, Any]) -> str:
        text = "<b>Old Chat Info</b>\n\n"
        text += f"<b>ID:</b> <code>{data['chat_id']}</code>\n"
        text += f"<b>Chat Name:</b> {escape(data['chat_name'])}\n"
        if self.predict_loaded:
            text += f"\n<b>Identifier:</b> <code>{data.get('hash', 'unknown')}</code>"
        return text

    async def cmd_info(self, ctx: command.Context, args: Optional[str] = None) -> Optional[str]:
        """Fetch a telegram peer data"""
        if not args:
            if ctx.msg.reply_to_message:
                if ctx.msg.reply_to_message.from_user:
                    return await self._user_info(ctx, ctx.msg.reply_to_message.from_user)
                if ctx.msg.reply_to_message.sender_chat:
                    return await self._chat_info(ctx, ctx.msg.reply_to_message.sender_chat)

            if not ctx.msg.reply_to_message:
                if not ctx.author:
                    return await self.get_text(ctx.chat.id, "err-anonymous")

                return await self._user_info(ctx, ctx.author)

            return

        id_match = None
        if self.predict_loaded:
            id_match = re.search(r"([a-fA-F\d]{32})", args)

        if id_match:
            user_data = await self.users_db.find_one({"hash": id_match.group(0)})
            if user_data:
                try:
                    user = await ctx.bot.client.get_users(user_data["_id"])
                    if isinstance(user, List):
                        user = user[0]

                    return await self._user_info(ctx, user)
                except PeerIdInvalid:
                    text = await self._old_user_info(user_data)
                    if text:
                        await ctx.respond(text, parse_mode=ParseMode.HTML)
                        return

            chat_data = await self.chats_db.find_one({"hash": id_match.group(0)})
            if chat_data:
                try:
                    chat = await ctx.bot.client.get_chat(chat_data["chat_id"])
                    return await self._chat_info(ctx, chat)
                except (PeerIdInvalid, ChannelInvalid, ChannelPrivate):
                    text = await self._old_chat_info(chat_data)
                    if text:
                        await ctx.respond(text, parse_mode=ParseMode.HTML)
                        return

            return await self.text(ctx.chat.id, "err-invalid-pid")

        try:
            user = await ctx.bot.client.get_users(args)
            if isinstance(user, List):
                user = user[0]

            return await self._user_info(ctx, user)
        except (IndexError, BadRequest):  # chat peer
            try:
                uid = int(args)
            except (TypeError, ValueError):
                pass
            else:
                try:
                    chat = await ctx.bot.client.get_chat(uid)
                    return await self._chat_info(ctx, chat)
                except (BadRequest, ChannelPrivate):
                    user = await self.users_db.find_one({"_id": uid})
                    if user:
                        text = await self._old_user_info(user)
                        if text:
                            await ctx.respond(text, parse_mode=ParseMode.HTML)
                            return

                    chat = await self.chats_db.find_one({"chat_id": uid})
                    if chat:
                        text = await self._old_chat_info(chat)
                        if text:
                            await ctx.respond(text, parse_mode=ParseMode.HTML)
                            return
        except KeyError:  # Rare case username expired, so make it recursively
            return await self.cmd_info(ctx, args)

        return await self.text(ctx.chat.id, "err-peer-invalid")
