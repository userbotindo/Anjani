"""Bot Federation Tools"""
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
from datetime import datetime
from typing import (
    Any,
    AsyncIterator,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Union,
)
from uuid import uuid4

from aiopath import AsyncPath
from pyrogram.enums.chat_member_status import ChatMemberStatus
from pyrogram.enums.chat_type import ChatType
from pyrogram.errors import (
    BadRequest,
    ChannelPrivate,
    ChatAdminRequired,
    Forbidden,
    PeerIdInvalid,
)
from pyrogram.types import (
    CallbackQuery,
    Chat,
    ChatMemberUpdated,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)

from anjani import command, filters, listener, plugin, util


class Federation(plugin.Plugin):
    name = "Federations"
    helpable = True

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("FEDERATIONS")

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_chat_action(self, message: Message) -> None:
        if message.left_chat_member:
            return

        chat = message.chat
        if not chat:
            return
        fed_data = await self.get_fed_bychat(chat.id)
        if not fed_data:
            return

        if message.new_chat_members:
            for new_member in message.new_chat_members:
                banned = await self.is_fbanned(chat.id, new_member.id)
                if banned:
                    await self.fban_handler(chat, new_member, banned)

        if message.left_chat_member and message.left_chat_member.id == self.bot.uid:
            fed_data = await self.get_fed_bychat(chat.id)
            if fed_data:
                # Leave the chat federation
                await self.db.update_one({"_id": fed_data["_id"]}, {"$pull": {"chats": chat.id}})

    async def on_chat_member_update(self, update: ChatMemberUpdated) -> None:
        """Leave federation if bot is demoted"""
        if not (update.old_chat_member and update.new_chat_member):
            return
        if update.old_chat_member.user.id != self.bot.uid:
            return

        old_priv = update.old_chat_member.privileges
        new_priv = update.new_chat_member.privileges

        if (old_priv and old_priv.can_restrict_members) and not (
            new_priv and new_priv.can_restrict_members
        ):
            chat = update.chat
            fed_data = await self.get_fed_bychat(chat.id)
            if not fed_data:
                return
            ret, _ = await asyncio.gather(
                self.text(chat.id, "fed-autoleave", fed_data["name"], fed_data["_id"]),
                self.db.update_one({"_id": fed_data["_id"]}, {"$pull": {"chats": chat.id}}),
            )
            await self.bot.client.send_message(chat.id, ret)

    @listener.filters(filters.regex(r"(rm|log)fed_(.*)"))
    async def on_callback_query(self, query: CallbackQuery) -> Any:
        """Delete federation button listener"""
        cmd = query.matches[0].group(1)
        arg = query.matches[0].group(2)
        chat = query.message.chat
        user = query.from_user

        if cmd == "rm":
            if arg == "abort":
                return await query.message.edit_text(
                    await self.text(chat.id, "fed-delete-canceled")
                )

            data = await self.db.find_one_and_delete({"_id": arg})
            await query.message.edit_text(await self.text(chat.id, "fed-delete-done", data["name"]))
        elif cmd == "log":
            owner_id, fid = arg.split("_")
            if user.id != int(owner_id):
                return await query.edit_message_text(
                    await self.text(chat.id, "fed-invalid-identity")
                )

            data = await self.db.find_one_and_update({"_id": fid}, {"$set": {"log": chat.id}})
            await query.edit_message_text(
                await self.text(chat.id, "fed-log-set-chnl", data["name"])
            )
        else:
            raise ValueError("Invalid callback data command")

    async def on_message(self, message: Message) -> None:
        if message.outgoing or not message.chat:
            return

        chat = message.chat
        if chat.type == ChatType.CHANNEL and message.text and message.text.startswith("/setfedlog"):
            return await self.channel_setlog(message)

        target = message.from_user or message.sender_chat
        if not target:
            return

        banned = await self.is_fbanned(chat.id, target.id)
        if banned:
            await self.fban_handler(chat, target, banned)

    @staticmethod
    def is_fed_admin(data: Mapping[str, Any], user: int) -> bool:
        """Check federation admin"""
        return user == data["owner"] or user in data.get("admins", [])

    async def get_fed_bychat(self, chat: int) -> Optional[Mapping[str, Any]]:
        return await self.db.find_one({"chats": chat})

    async def get_fed_byowner(self, user: int) -> Optional[Mapping[str, Any]]:
        return await self.db.find_one({"owner": user})

    async def get_fed(self, fid: str) -> Optional[Mapping[str, Any]]:
        return await self.db.find_one({"_id": fid})

    async def _get_fed_subs_str(self, fid: str) -> Optional[str]:
        """Get federation that subcribe current federation as string"""
        res = ""
        async for i in self.db.find({"subscribers": fid}):
            res += f"- **{i['name']}** (`{i['_id']}`)\n"
        return res or None

    async def _get_fed_subs_data(self, fid: str) -> AsyncIterator[Mapping[str, Any]]:
        """Get federation that subcribe current federation"""
        async for i in self.db.find(
            {"subscribers": fid}, {"_id": 1, "name": 1, "banned": 1, "banned_chat": 1}
        ):
            yield i

    async def fban_user(
        self,
        fid: str,
        user: int,
        *,
        fullname: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Fban a user"""
        await self.db.update_one(
            {"_id": fid},
            {
                "$set": {
                    f"banned.{user}": {"name": fullname, "reason": reason, "time": datetime.now()}
                }
            },
            upsert=True,
        )

    async def fban_chat(
        self,
        fid: str,
        chat: int,
        *,
        title: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Fban a channel"""
        await self.db.update_one(
            {"_id": fid},
            {
                "$set": {
                    f"banned_chat.{chat}": {
                        "title": title,
                        "reason": reason,
                        "time": datetime.now(),
                    }
                }
            },
        )

    async def unfban_user(self, fid: str, user: int) -> None:
        """Remove banned user"""
        await self.db.update_one({"_id": fid}, {"$unset": {f"banned.{user}": None}}, upsert=True)

    async def unfban_chat(self, fid: str, chat: int) -> None:
        """Remove banned chat"""
        await self.db.update_one(
            {"_id": fid}, {"$unset": {f"banned_chat.{chat}": None}}, upsert=True
        )

    async def check_fban(self, target: int) -> util.db.AsyncCursor:
        """Check user banned list"""
        return self.db.find(
            {
                "$or": [
                    {f"banned.{target}": {"$exists": True}},
                    {f"banned_chat.{target}": {"$exists": True}},
                ]
            },
            {
                "_id": 1,
                "name": 1,
                f"banned.{target}": 1,
                f"banned_chat.{target}": 1,
            },
        )

    async def is_fbanned(self, chat: int, target: int) -> Optional[MutableMapping[str, Any]]:
        def check(target: int, data: Mapping[str, Any]) -> Optional[MutableMapping[str, Any]]:
            """Scoped check to verify if user is banned"""
            if str(target) in data.get("banned", {}):
                user_data = data["banned"][str(target)]
                user_data["fed_name"] = data["name"]
                user_data["type"] = "user"
                return user_data

            if str(target) in data.get("banned_chat", {}):
                channel_data = data["banned_chat"][str(target)]
                channel_data["fed_name"] = data["name"]
                channel_data["type"] = "chat"
                return channel_data

        data = await self.db.find_one(
            {
                "chats": chat,
                "$or": [
                    {f"banned.{target}": {"$exists": True}},
                    {f"banned_chat.{target}": {"$exists": True}},
                ],
            },
            {
                f"banned.{target}": 1,
                f"banned_chat.{target}": 1,
                "name": 1,
            },
        )
        if data:
            res = check(target, data)
            if res:
                return res

        # Check if user is banned in subcribed federation
        fid = await self.get_fed_bychat(chat)
        if not fid:
            return None

        subscribe = [res async for res in self._get_fed_subs_data(fid["_id"])]
        if not subscribe:
            return None
        for i in subscribe:
            res = check(target, i)
            if res:
                res["subfed"] = True
                return res

    async def fban_handler(
        self, chat: Chat, user: Union[User, Chat], data: MutableMapping[str, Any]
    ) -> None:
        string = "fed-autoban"
        if data["type"] != "user":
            string += "-chat"
        if data.get("subfed", False):
            string += "-subfed"

        try:
            await asyncio.gather(
                self.bot.client.send_message(
                    chat.id,
                    await self.text(
                        chat.id,
                        string,
                        user.mention
                        if (data["type"] == "user" and isinstance(user, User))
                        else data["title"],
                        data["fed_name"],
                        data["reason"],
                        data["time"].strftime("%Y %b %d %H:%M UTC"),
                    ),
                ),
                self.bot.client.ban_chat_member(chat.id, user.id),
            )
        except ChatAdminRequired:
            self.log.debug(f"Can't ban user {user.username} on {chat.title}")

    async def cmd_newfed(self, ctx: command.Context, name: Optional[str] = None) -> str:
        """Create a new federations"""
        chat = ctx.chat
        if chat.type != ChatType.PRIVATE:
            return await self.text(chat.id, "err-chat-private")

        if not name:
            return await self.text(chat.id, "need-fed-name")

        fed_id = str(uuid4())
        owner = ctx.msg.from_user

        exists = await self.db.find_one({"owner": owner.id})
        if exists:
            return await self.text(chat.id, "federation-limit")

        await self.db.insert_one({"_id": fed_id, "name": name, "owner": owner.id, "log": owner.id})
        return await self.text(chat.id, "new-federation", fed_name=name, fed_id=fed_id)

    async def cmd_delfed(self, ctx: command.Context) -> Optional[str]:
        """Delete federations"""
        chat = ctx.chat
        if chat.type != ChatType.PRIVATE:
            return await self.text(chat.id, "err-chat-private")

        owner = ctx.msg.from_user

        exists = await self.db.find_one({"owner": owner.id})
        if not exists:
            return await self.text(chat.id, "user-no-feds")

        await ctx.respond(
            await self.text(chat.id, "del-fed-confirm", exists["name"]),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=await self.text(chat.id, "fed-confirm-text"),
                            callback_data="rmfed_" + exists["_id"],
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=await self.text(chat.id, "fed-abort-text"),
                            callback_data="rmfed_abort",
                        )
                    ],
                ]
            ),
        )
        return None

    @command.filters(filters.admin_only & filters.can_restrict)
    async def cmd_joinfed(self, ctx: command.Context, fid: Optional[str] = None) -> str:
        """Join a federation in chats"""
        chat = ctx.chat
        user = ctx.msg.from_user

        invoker = await chat.get_member(user.id)
        if invoker.status != ChatMemberStatus.OWNER:
            return await self.text(chat.id, "err-group-creator-cmd")

        if not fid:
            return await self.text(chat.id, "fed-not-found")

        if await self.get_fed_bychat(chat.id):
            return await self.text(chat.id, "fed-cant-two-feds")

        data = await self.get_fed(fid)
        if not data:
            return await self.text(chat.id, "fed-invalid-id")

        if chat.id in data.get("chats", []):
            return await self.text(chat.id, "fed-already-connected")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "fed-chat-joined-info", data["name"]),
            self.db.update_one({"_id": fid}, {"$push": {"chats": chat.id}}),
        )
        if log := data.get("log"):
            await self.bot.client.send_message(
                log,
                f"**New Chat Joined Federation**\n**Name**: {chat.title}",
            )

        return ret

    @command.filters(filters.admin_only)
    async def cmd_leavefed(self, ctx: command.Context, fid: Optional[str] = None) -> str:
        """Leave a federation in chats"""
        chat = ctx.chat
        user = ctx.msg.from_user

        invoker = await chat.get_member(user.id)
        if invoker.status != ChatMemberStatus.OWNER or invoker.user.id != self.bot.owner:
            return await self.text(chat.id, "err-group-creator-cmd")

        if not fid:
            return await self.text(chat.id, "fed-not-found")

        exists = await self.get_fed(fid)
        if not exists:
            return await self.text(chat.id, "fed-invalid-id")

        if chat.id not in exists.get("chats", []):
            return await self.text(chat.id, "fed-not-connected")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "fed-chat-leave-info", exists["name"]),
            self.db.update_one({"_id": fid}, {"$pull": {"chats": chat.id}}),
        )
        return ret

    @command.filters(aliases=["fpromote"])
    async def cmd_fedpromote(self, ctx: command.Context, user: Optional[User] = None) -> str:
        """Promote user to fed admin"""
        chat = ctx.chat
        if chat.type == ChatType.PRIVATE:
            return await self.text(chat.id, "err-chat-groups")

        if not user:
            if not ctx.msg.reply_to_message:
                return await self.text(chat.id, "fed-no-promote-user")
            user = ctx.msg.reply_to_message.from_user

        data = await self.get_fed_bychat(chat.id)
        if not data:
            return await self.text(chat.id, "fed-no-fed-chat")

        if ctx.author.id != data["owner"]:
            return await self.text(chat.id, "fed-owner-only-promote")
        if user.id == data["owner"]:
            return await self.text(chat.id, "fed-already-owner")
        if user.id in data.get("admins", []):
            return await self.text(chat.id, "fed-already-admin")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "fed-promote-done"),
            self.db.update_one({"_id": data["_id"]}, {"$push": {"admins": user.id}}),
        )
        if log := data.get("log"):
            await self.bot.client.send_message(
                log,
                "**New Fed Promotion**\n"
                "**Fed**: " + data["name"] + "\n"
                f"**Promoted FedAdmin**: {user.mention}\n"
                f"**User ID**: `{user.id}`",
            )

        return ret

    @command.filters(aliases=["fdemote"])
    async def cmd_feddemote(self, ctx: command.Context, user: Optional[User] = None) -> str:
        """Demote user to fed admin"""
        chat = ctx.chat
        if chat.type == ChatType.PRIVATE:
            return await self.text(chat.id, "err-chat-groups")

        invoker = ctx.msg.from_user
        if not user:
            if not ctx.msg.reply_to_message:
                return await self.text(chat.id, "fed-no-demote-user")
            user = ctx.msg.reply_to_message.from_user

        data = await self.get_fed_bychat(chat.id)
        if not data:
            return await self.text(chat.id, "fed-no-fed-chat")

        if invoker.id != data["owner"]:
            return await self.text(chat.id, "fed-owner-only-demote")
        if user.id == data["owner"]:
            return await self.text(chat.id, "fed-already-owner")
        if user.id not in data.get("admins", []):
            return await self.text(chat.id, "fed-user-not-admin")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "fed-demote-done"),
            self.db.update_one({"_id": data["_id"]}, {"$pull": {"admins": user.id}}),
        )
        if log := data.get("log"):
            await self.bot.client.send_message(
                log,
                "**New Fed Demotion**\n"
                "**Fed**: " + data["name"] + "\n"
                f"**Promoted FedAdmin**: {user.mention}\n"
                f"**User ID**: `{user.id}`",
            )

        return ret

    async def cmd_fedinfo(self, ctx: command.Context, fid: Optional[str] = None) -> str:
        """Fetch federation info"""
        chat = ctx.chat

        if fid is not None:
            data = await self.get_fed(fid)
            if not data:
                return await self.text(chat.id, "fed-invalid-id")
        elif chat.type != ChatType.PRIVATE:
            data = await self.get_fed_bychat(chat.id)
            if not data:
                return (
                    await self.text(chat.id, "fed-no-fed-chat")
                    + "\n"
                    + await self.text(chat.id, "fed-specified-id")
                )
        else:
            return await self.text(chat.id, "fed-specified-id")

        owner = await self.bot.client.get_users(data["owner"])
        if isinstance(owner, List):
            owner = owner[0]

        res = await self.text(
            chat.id,
            "fed-info-text",
            data["_id"],
            data["name"],
            owner.mention,
            len(data.get("admins", [])),
            len(data.get("banned", [])),
            len(data.get("banned_chat", [])),
            len(data.get("chats", [])),
            len(data.get("subscribers", [])),
        )
        if subs := await self._get_fed_subs_str(data["_id"]):
            res += await self.text(chat.id, "fed-info-subscription") + f"{subs}"
        return res

    @command.filters(aliases=["fedadmin", "fadmin", "fadmins"])
    async def cmd_fedadmins(self, ctx: command.Context, fid: Optional[str] = None) -> str:
        """Fetch federation admins"""
        chat = ctx.chat
        user = ctx.msg.from_user

        if fid:
            data = await self.get_fed(fid)
            text = await self.text(chat.id, "fed-invalid-id")
        else:
            data = await self.get_fed_bychat(chat.id)
            text = await self.text(chat.id, "fed-no-fed-chat")

        if not data:
            return text

        if not self.is_fed_admin(data, user.id):
            return await self.text(chat.id, "fed-admin-only")

        owner = await self.bot.client.get_users(data["owner"])
        if isinstance(owner, List):
            owner = owner[0]

        text = await self.text(chat.id, "fed-admin-text", data["name"], owner.mention)
        if len(data.get("admins", [])) != 0:
            text += "\nAdmins:\n"
            admins = []
            for admin in data["admins"]:
                admins.append(admin)

            for uid in admins:
                try:
                    admin = await self.bot.client.get_users(uid)
                except PeerIdInvalid:
                    text += f"[{uid}](tg://user?id={uid})\n"
                    continue

                text += f" • {admin.mention}\n"  # type: ignore
        else:
            text += "\n" + await self.text(chat.id, "fed-no-admin")

        return text

    async def __user_fban(
        self,
        chat: Chat,
        target: User,
        banner: User,
        reason: str,
        fed_data: Mapping[str, Any],
    ) -> str:
        update = False
        if str(target.id) in fed_data.get("banned", {}).keys():
            update = True

        fullname = target.first_name + target.last_name if target.last_name else target.first_name
        await self.fban_user(fed_data["_id"], target.id, fullname=fullname, reason=reason)

        if update:
            return await self.text(
                chat.id,
                "fed-ban-info-update",
                fed_data["name"],
                banner.mention,
                target.mention,
                target.id,
                fed_data["banned"][str(target.id)]["reason"],
                reason,
            )
        return await self.text(
            chat.id,
            "fed-ban-info",
            fed_data["name"],
            banner.mention,
            target.mention,
            target.id,
            reason,
        )

    async def __channel_fban(
        self,
        chat: Chat,
        target: Chat,
        banner: User,
        reason: str,
        fed_data: Mapping[str, Any],
    ) -> str:
        update = False
        if str(target.id) in fed_data.get("banned_chat", {}).keys():
            update = True

        await self.fban_chat(fed_data["_id"], target.id, title=target.title, reason=reason)

        if update:
            return await self.text(
                chat.id,
                "fed-ban-chat-info-update",
                fed_data["name"],
                banner.mention,
                target.title,
                target.id,
                fed_data["banned_chat"][str(target.id)]["reason"],
                reason,
            )
        return await self.text(
            chat.id,
            "fed-ban-chat-info",
            fed_data["name"],
            banner.mention,
            target.title,
            target.id,
            reason,
        )

    async def cmd_fban(
        self, ctx: command.Context, target: Union[User, Chat, None] = None, *, reason: str = ""
    ) -> Optional[str]:
        """Fed ban command"""
        chat = ctx.chat
        if chat.type == ChatType.PRIVATE:
            return await self.text(chat.id, "err-chat-groups")

        banner = ctx.msg.from_user
        if not banner:
            return await self.text(chat.id, "err-anonymous")

        data = await self.get_fed_bychat(chat.id)
        if not data:
            return await self.text(chat.id, "fed-no-fed-chat")

        if not self.is_fed_admin(data, banner.id):
            return await self.text(chat.id, "fed-admin-only")

        reply_msg = ctx.msg.reply_to_message
        if not target:
            if ctx.args and not reply_msg:
                return await self.text(chat.id, "err-peer-invalid")

            if not reply_msg or not (reply_msg.from_user or reply_msg.sender_chat):
                return await self.text(chat.id, "fed-no-ban-user")

            target = reply_msg.from_user or reply_msg.sender_chat
            reason = ctx.input

        if target.id == self.bot.uid:
            return await self.text(chat.id, "fed-ban-self")
        if self.is_fed_admin(data, target.id):
            return await self.text(chat.id, "fed-ban-owner")
        if (
            target.id in self.bot.staff
            or target.id in (777000, 1087968824)
            or target.id == self.bot.owner
        ):
            return await self.text(chat.id, "fed-ban-protected")

        if not reason:
            reason = "No reason given."

        if isinstance(target, User):
            string = await self.__user_fban(chat, target, banner, reason, data)
        elif isinstance(target, Chat):
            string = await self.__channel_fban(chat, target, banner, reason, data)
        else:
            return await self.text(chat.id, "err-peer-invalid")

        failed: Dict[int, Optional[str]] = {}
        for chat in data["chats"]:
            try:
                await self.bot.client.ban_chat_member(chat, target.id)
            except BadRequest as br:
                self.log.warning(f"Failed to fban {target.username} on {chat} due to {br.MESSAGE}")
                failed[chat] = br.MESSAGE
            except (Forbidden, ChannelPrivate) as err:
                self.log.warning(
                    f"Can't to fban {target.username} on {chat} caused by {err.MESSAGE}"
                )
                failed[chat] = err.MESSAGE

        text = ""
        if failed:
            for key, err_msg in failed.items():
                text += f"failed to fban on chat {key} caused by {err_msg}\n\n"
                # Remove the chat federation
                await self.db.update_one({"_id": data["_id"]}, {"$pull": {"chats": chat}})
            text += f"**Those chat has leaved the federation {data['name']}!**"
            await ctx.respond(text, mode="reply", reference=ctx.response)

        if data.get("subscribers", []):
            for fed_id in data["subscribers"]:
                subs_data = await self.get_fed(fed_id)
                if not subs_data:
                    continue
                for chat in subs_data.get("chats", []):
                    try:
                        await self.bot.client.ban_chat_member(chat, target.id)
                    except BadRequest as br:
                        self.log.warning(
                            f"Failed to send fban on subfed {subs_data['_id']} of {data['_id']} at {chat} due to {br.MESSAGE}"
                        )
                    except (Forbidden, ChannelPrivate) as err:
                        self.log.warning(
                            f"Can't to fban on subfed {subs_data['_id']} of {data['_id']} at {chat} caused by {err.MESSAGE}"
                        )

        await ctx.respond(string)

        # send message to federation log
        if log := data.get("log"):
            await self.bot.client.send_message(log, string, disable_web_page_preview=True)
            if failed:
                await self.bot.client.send_message(log, text)

        return None

    async def cmd_unfban(self, ctx: command.Context, target: Union[User, Chat, None] = None) -> str:
        """Unban a user on federation"""
        chat = ctx.chat
        if chat.type == ChatType.PRIVATE:
            return await self.text(chat.id, "err-chat-groups")

        banner = ctx.msg.from_user
        if not banner:
            return await self.text(chat.id, "err-anonymous")

        data = await self.get_fed_bychat(chat.id)
        if not data:
            return await self.text(chat.id, "fed-no-fed-chat")

        if not self.is_fed_admin(data, banner.id):
            return await self.text(chat.id, "fed-admin-only")

        reply_msg = ctx.msg.reply_to_message
        if not target:
            if ctx.args and not reply_msg:
                return await self.text(chat.id, "err-peer-invalid")
            if not reply_msg or not (reply_msg.from_user or reply_msg.sender_chat):
                return await self.text(chat.id, "fed-no-ban-user")
            target = reply_msg.from_user or reply_msg.sender_chat

        if (str(target.id) not in (data.get("banned", {}).keys())) and (
            str(target.id) not in (data.get("banned_chat", {}).keys())
        ):
            return await self.text(chat.id, "fed-user-not-banned")

        if isinstance(target, User):
            await self.unfban_user(data["_id"], target.id)
            text = await self.text(
                chat.id,
                "fed-unban-info",
                data["name"],
                banner.mention,
                target.mention,
                target.id,
            )
        elif isinstance(target, Chat):
            await self.unfban_chat(data["_id"], target.id)
            text = await self.text(
                chat.id,
                "fed-unban-info-chat",
                data["name"],
                banner.mention,
                target.title,
                target.id,
            )
        else:
            return ""

        for chat in data["chats"]:
            try:
                await self.bot.client.unban_chat_member(chat, target.id)
            except (BadRequest, Forbidden, ChannelPrivate) as err:
                self.log.warning(f"Failed to unfban on {data['_id']} due to {err.MESSAGE}")

        if data.get("subscribers", []):
            for fed_id in data["subscribers"]:
                subs_data = await self.get_fed(fed_id)
                if not subs_data:
                    continue
                for chat in subs_data.get("chats", []):
                    try:
                        await self.bot.client.unban_chat_member(chat, target.id)
                    except (BadRequest, Forbidden, ChannelPrivate) as err:
                        self.log.warning(
                            f"Failed to unfban on subfed {subs_data['_id']} of {data['_id']} due to {err.MESSAGE}"
                        )

        if log := data.get("log"):
            await self.bot.client.send_message(log, text, disable_web_page_preview=True)

        return text

    @command.filters(aliases=["fstats", "fedstats"])
    async def cmd_fbanstats(self, ctx: command.Context) -> str:
        """Get user status"""
        chat = ctx.chat
        if len(ctx.args) > 1:  # <user_id> <fed_id>
            try:
                user_id = int(ctx.args[0])
            except TypeError:
                return await self.text(chat.id, "fed-invalid-user-id")

            data = await self.get_fed(ctx.args[1])
            if data:
                if str(user_id) in data.get("banned", {}):
                    res = data["banned"][str(user_id)]
                    return await self.text(
                        chat.id,
                        "fed-stat-banned",
                        res["reason"],
                        res["time"].strftime("%Y %b %d %H:%M UTC"),
                    )
                if str(user_id) in data.get("banned_chat", {}):
                    res = data["banned_chat"][str(user_id)]
                    return await self.text(
                        chat.id,
                        "fed-stat-banned-chat",
                        res["reason"],
                        res["time"].strftime("%Y %b %d %H:%M UTC"),
                    )

                if str(user_id) in data.get("banned_chat", {}):
                    res = data["banned_chat"][str(user_id)]
                    return await self.text(
                        chat.id,
                        "fed-stat-banned-chat",
                        res["reason"],
                        res["time"].strftime("%Y %b %d %H:%M UTC"),
                    )
                return await self.text(chat.id, "fed-stat-not-banned")
            return await self.text(chat.id, "fed-not-found")

        user = None
        user_id = None
        if len(ctx.args) == 1:  # <user_id>
            try:
                user_id = int(ctx.args[0])
                user = await self.bot.client.get_users(user_id)
                if isinstance(user, List):
                    user = user[0]
                if not user:
                    return await self.text(chat.id, "fed-invalid-user-id")
            except TypeError:
                return await self.text(chat.id, "fed-invalid-user-id")

        reply_msg = ctx.msg.reply_to_message
        if not user_id:
            if reply_msg:
                user = reply_msg.from_user or reply_msg.sender_chat
            else:
                user = ctx.msg.from_user
            user_id = user.id

        if not user:
            return ""

        cursor = await self.check_fban(user_id)
        fed_list = await cursor.to_list()
        if fed_list:
            text = await self.text(chat.id, "fed-stat-multi")
            for bans in fed_list:
                text += "\n" + await self.text(
                    chat.id,
                    "fed-stat-multi-info",
                    bans["name"],
                    bans["_id"],
                    bans["banned_chat" if bans.get("banned_chat") else "banned"][str(user.id)][
                        "reason"
                    ],
                )
        else:
            text = await self.text(chat.id, "fed-stat-multi-not-banned")

        return text

    @command.filters(filters.private)
    async def cmd_fedbackup(self, ctx: command.Context) -> Optional[str]:
        """Backup federation ban list"""
        chat = ctx.chat
        user = ctx.msg.from_user

        data = await self.db.find_one({"owner": user.id})
        if not data:
            return await self.text(chat.id, "user-no-feds")

        try:
            banned = data["banned"]
        except KeyError:
            return await self.text(chat.id, "fed-backup-empty")

        file = AsyncPath(
            self.bot.config.get("download_path", "./downloads/") + data["name"] + ".csv"
        )

        await file.touch()
        async with file.open("w") as f:
            for banned_user in banned:
                ban_data = banned[banned_user]
                await f.write(
                    f"{banned_user},{ban_data['name']},{ban_data['reason']},{ban_data['time']}\n"
                )

        await ctx.respond(document=str(file))
        await file.unlink()
        return None

    @command.filters(filters.private)
    async def cmd_fedrestore(self, ctx: command.Context) -> Optional[str]:
        """Restore a backup bans"""
        chat = ctx.chat
        user = ctx.msg.from_user
        reply_msg = ctx.msg.reply_to_message
        if not (reply_msg and reply_msg.document):
            return await self.text(chat.id, "no-backup-file")

        data = await self.db.find_one({"owner": user.id})
        if not data:
            return await self.text(chat.id, "user-no-feds")

        file = AsyncPath(
            await reply_msg.download(self.bot.config.get("download_path", "./downloads/"))
        )

        fid = data["_id"]
        tasks = []  # type: List[asyncio.Task[None]]
        async with file.open("r") as f:
            line: str
            async for line in f:  # type: ignore
                d = line.split(",")
                task = self.bot.loop.create_task(
                    self.fban_user(fid, int(d[0]), fullname=d[1], reason=d[2])
                )
                tasks.append(task)

        ret = await asyncio.gather(self.text(chat.id, "fed-restore-done"), file.unlink(), *tasks)
        return ret[0]

    @command.filters(filters.private, aliases=["myfeds"])
    async def cmd_myfed(self, ctx: command.Context) -> str:
        """Get current users federation"""
        chat = ctx.chat
        user = ctx.msg.from_user

        data = await self.db.find_one({"owner": user.id})
        if data:
            return (
                await self.text(chat.id, "fed-myfeds-owner")
                + f"\n- `{data['_id']}`: {data['name']}"
            )

        cursor = self.db.find({"admins": user.id}, {"_id": 1, "name": 1})
        fed_list = await cursor.to_list()
        if fed_list:
            text = await self.text(chat.id, "fed-myfeds-admin") + "\n"
            for fed in fed_list:
                text += f"- `{fed['_id']}`: {fed['name']}\n"

            return text

        return await self.text(chat.id, "fed-myfeds-no-admin")

    def generate_log_btn(self, data: Mapping[str, Any]) -> InlineKeyboardMarkup:
        """Generate log channel verify button"""
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Click to confirm identity",
                        callback_data=f"logfed_{data['owner']}_{data['_id']}",
                    )
                ],
            ]
        )

    async def channel_setlog(self, message: Message):
        fid = message.text.split(" ")
        if not fid or len(fid) < 2:
            await message.reply_text(await self.text(message.chat.id, "fed-set-log-args"))
            return
        data = await self.get_fed(fid[1])
        if not data:
            await message.reply_text(await self.text(message.chat.id, "fed-not-found"))
            return
        await message.reply_text(
            await self.text(message.chat.id, "fed-check-identity"),
            reply_markup=self.generate_log_btn(data),
        )

    async def cmd_setfedlog(self, ctx: command.Context, fid: Optional[str] = None) -> Optional[str]:
        """Set a federation log channel"""
        chat = ctx.chat
        if chat.type == ChatType.CHANNEL:
            if not fid:
                return await self.text(chat.id, "fed-set-log-args")

            data = await self.get_fed(fid)
            if not data:
                return await self.text(chat.id, "Fed not found!")

            await ctx.respond(
                await self.text(chat.id, "fed-check-identity"),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Click to confirm identity",
                                callback_data=f"logfed_{data['owner']}_{data['_id']}",
                            )
                        ],
                    ]
                ),
            )
            return None

        if chat.type in {ChatType.GROUP, ChatType.SUPERGROUP}:
            data = await self.get_fed_byowner(ctx.author.id)
            if not data:
                return await self.text(chat.id, "user-no-feds")

            ret, _ = await asyncio.gather(
                self.text(chat.id, "fed-log-set-group", name=data["name"]),
                self.db.update_one({"_id": data["_id"]}, {"$set": {"log": chat.id}}),
            )
            return ret

        return await self.text(chat.id, "err-chat-groups")

    async def cmd_unsetfedlog(self, ctx: command.Context) -> str:
        """Unset the federation log channel"""
        chat = ctx.chat
        user = ctx.msg.from_user
        if chat.type == ChatType.PRIVATE:
            data = await self.get_fed_byowner(user.id)
            if not data:
                return await self.text(chat.id, "user-no-feds")

            ret, _ = await asyncio.gather(
                self.text(chat.id, "fed-log-unset", data["name"]),
                self.db.update_one({"_id": data["_id"]}, {"$set": {"log": None}}),
            )
            return ret

        return await self.text(chat.id, "err-chat-private")

    async def _subfed_perm_check(self, ctx: command.Context, fid: Optional[str] = None):
        """Check if able to subscribe to a fed and returns current and target federation"""
        if not fid:
            await ctx.respond(await self.text(ctx.chat.id, "fed-not-found"))
            return None
        if ctx.chat.type == ChatType.PRIVATE:
            await ctx.respond(await self.text(ctx.chat.id, "err-chat-groups"))
            return None

        curr_fed = await self.get_fed_bychat(ctx.chat.id)
        target = await self.get_fed(fid)
        if not curr_fed:
            await ctx.respond(await self.text(ctx.chat.id, "fed-no-fed-chat"))
            return None
        if curr_fed["owner"] != ctx.author.id:
            await ctx.respond(await self.text(ctx.chat.id, "fed-owner-cmd"))
            return None
        if not target:
            await ctx.respond(await self.text(ctx.chat.id, "fed-not-found"))
            return None

        return (curr_fed, target)

    async def cmd_subfed(self, ctx: command.Context, fid: Optional[str] = None):
        """Subscribe to a federation"""
        res = await self._subfed_perm_check(ctx, fid)
        if not res:
            return
        curr_fed, to_subs = res

        await self.db.update_one({"_id": fid}, {"$push": {"subscribers": curr_fed["_id"]}})
        try:
            await self.bot.client.send_message(
                to_subs["log"] or to_subs["owner"],
                f"Federation {curr_fed['name']} has subscribed to {to_subs['name']}",
            )
        except PeerIdInvalid:
            self.log.warning("Failed to send fed-subs message to log channel")

        return await self.text(ctx.chat.id, "fed-subs-join", curr_fed["name"], to_subs["name"])

    async def cmd_unsubfed(self, ctx: command.Context, fid: Optional[str] = None):
        """Unsubscribe from a federation"""
        res = await self._subfed_perm_check(ctx, fid)
        if not res:
            return
        curr_fed, to_unsubs = res

        await self.db.update_one({"_id": fid}, {"$pull": {"subscribers": curr_fed["_id"]}})
        try:
            await self.bot.client.send_message(
                to_unsubs["log"],
                f"Federation **{curr_fed['name']}** has unsubscribed from **{to_unsubs['name']}**",
            )
        except PeerIdInvalid:
            self.log.warning("Failed to send unsubs message to log channel")

        return await self.text(ctx.chat.id, "fed-subs-leave", curr_fed["name"], to_unsubs["name"])
