"""Bot Federation Tools"""
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

import asyncio
from datetime import datetime
from typing import Any, Dict, List, MutableMapping, Optional
from uuid import uuid4

from aiopath import AsyncPath
from pyrogram.errors import BadRequest, ChatAdminRequired, Forbidden
from pyrogram.types import (
    CallbackQuery,
    Chat,
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
        fed_data = await self.get_fed_bychat(chat.id)
        if not fed_data:
            return

        for new_member in message.new_chat_members:
            banned = await self.is_fbanned(chat.id, new_member.id)
            if banned:
                await self.fban_handler(message.chat, new_member, banned)

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
        chat = message.chat
        user = message.from_user
        if not user:
            return

        banned = await self.is_fbanned(chat.id, user.id)
        if banned:
            await self.fban_handler(message.chat, user, banned)

    @staticmethod
    def is_fed_admin(data: MutableMapping[str, Any], user: int) -> bool:
        """Check federation admin"""
        return user == data["owner"] or user in data.get("admins", [])

    async def get_fed_bychat(self, chat: int) -> Optional[MutableMapping[str, Any]]:
        return await self.db.find_one({"chats": chat})

    async def get_fed_byowner(self, user: int) -> Optional[MutableMapping[str, Any]]:
        return await self.db.find_one({"owner": user})

    async def get_fed(self, fid: str) -> Optional[MutableMapping[str, Any]]:
        return await self.db.find_one({"_id": fid})

    async def fban_user(
        self,
        fid: str,
        user: int,
        *,
        fullname: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Ban a user"""
        await self.db.update_one(
            {"_id": fid},
            {
                "$set": {
                    f"banned.{user}": {"name": fullname, "reason": reason, "time": datetime.now()}
                }
            },
            upsert=True,
        )

    async def unfban_user(self, fid: str, user: int) -> None:
        """Remove banned user"""
        await self.db.update_one({"_id": fid}, {"$unset": {f"banned.{user}": None}}, upsert=True)

    async def check_fban(self, user: int) -> Optional[util.db.AsyncCursor]:
        """Check user banned list"""
        query = {f"banned.{user}": {"$exists": True}}
        projection = {f"banned.{user}": 1, "name": 1, "chats": 1}

        empty = await self.db.count_documents(query) == 0
        return self.db.find(query, projection=projection) if not empty else None

    async def is_fbanned(self, chat: int, user: int) -> Optional[MutableMapping[str, Any]]:
        data = await self.get_fed_bychat(chat)
        if not data or str(user) not in data.get("banned", {}):
            return None

        user_data = data["banned"][str(user)]
        user_data["fed_name"] = data["name"]
        return user_data

    async def fban_handler(self, chat: Chat, user: User, data: MutableMapping[str, Any]) -> None:
        try:
            await asyncio.gather(
                self.bot.client.send_message(
                    chat.id,
                    await self.text(
                        chat.id,
                        "fed-autoban",
                        util.tg.mention(user),
                        data["fed_name"],
                        data["reason"],
                        data["time"].strftime("%Y %b %d %H:%M UTC"),
                    ),
                ),
                self.bot.client.kick_chat_member(chat.id, user.id),
            )
        except ChatAdminRequired:
            self.log.debug(f"Can't ban user {user.username} on {chat.title}")

    async def cmd_newfed(self, ctx: command.Context, name: Optional[str] = None) -> str:
        """Create a new federations"""
        chat = ctx.chat
        if chat.type != "private":
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
        if chat.type != "private":
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

    @command.filters(filters.admin_only)
    async def cmd_joinfed(self, ctx: command.Context, fid: Optional[str] = None) -> str:
        """Join a federation in chats"""
        chat = ctx.chat
        user = ctx.msg.from_user

        invoker = await chat.get_member(user.id)
        if invoker.status != "creator":
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
        if invoker.status != "creator" or invoker.user.id != self.bot.owner:
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
        if chat.type == "private":
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
                f"**Promoted FedAdmin**: {util.tg.mention(user)}\n"
                f"**User ID**: `{user.id}`",
            )

        return ret

    @command.filters(aliases=["fdemote"])
    async def cmd_feddemote(self, ctx: command.Context, user: Optional[User] = None) -> str:
        """Demote user to fed admin"""
        chat = ctx.chat
        if chat.type == "private":
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
                f"**Promoted FedAdmin**: {util.tg.mention(user)}\n"
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
        elif chat.type != "private":
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

        return await self.text(
            chat.id,
            "fed-info-text",
            data["_id"],
            data["name"],
            util.tg.mention(owner),
            len(data.get("admins", [])),
            len(data.get("banned", [])),
            len(data.get("chats", [])),
        )

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

        text = await self.text(chat.id, "fed-admin-text", data["name"], util.tg.mention(owner))
        if len(data.get("admins", [])) != 0:
            text += "\nAdmins:\n"
            admins = []
            for admin in data["admins"]:
                admins.append(admin)

            admins = await self.bot.client.get_users(admins)
            for admin in admins:
                text += f" • {util.tg.mention(admin)}\n"
        else:
            text += "\n" + await self.text(chat.id, "fed-no-admin")

        return text

    async def cmd_fban(
        self, ctx: command.Context, user: Optional[User] = None, *, reason: str = ""
    ) -> Optional[str]:
        """Fed ban a user"""
        chat = ctx.chat
        if chat.type == "private":
            return await self.text(chat.id, "err-chat-groups")

        banner = ctx.msg.from_user
        if not banner:
            return await self.text(chat.id, "err-anonymous")

        data = await self.get_fed_bychat(chat.id)
        if not data:
            return await self.text(chat.id, "fed-no-fed-chat")

        if not self.is_fed_admin(data, banner.id):
            return await self.text(chat.id, "fed-admin-only")

        if not user:
            if ctx.args and not ctx.msg.reply_to_message:
                return await self.text(chat.id, "fed-no-ban-user")
            user = ctx.msg.reply_to_message.from_user
            reason = ctx.input

        if user.id == self.bot.uid:
            return await self.text(chat.id, "fed-ban-self")
        if self.is_fed_admin(data, user.id):
            return await self.text(chat.id, "fed-ban-owner")
        if (
            user.id in self.bot.staff
            or user.id in (777000, 1087968824)
            or user.id == self.bot.owner
        ):
            return await self.text(chat.id, "fed-ban-protected")

        if not reason:
            reason = "No reason given."

        update = False
        if str(user.id) in data.get("banned", {}).keys():
            update = True

        fullname = user.first_name + user.last_name if user.last_name else user.first_name
        await self.fban_user(data["_id"], user.id, fullname=fullname, reason=reason)

        if update:
            string = await self.text(
                chat.id,
                "fed-ban-info-update",
                data["name"],
                util.tg.mention(banner),
                util.tg.mention(user),
                user.id,
                data["banned"][str(user.id)]["reason"],
                reason,
            )
        else:
            string = await self.text(
                chat.id,
                "fed-ban-info",
                data["name"],
                util.tg.mention(banner),
                util.tg.mention(user),
                user.id,
                reason,
            )

        failed: Dict[int, str] = {}
        for chat in data["chats"]:
            try:
                await self.bot.client.kick_chat_member(chat, user.id)
            except BadRequest as br:
                self.log.error(f"Failed to fban {user.username} due to {br.MESSAGE}")
                failed[chat] = br.MESSAGE
            except Forbidden as err:
                self.log.error(f"Can't to fban {user.username} caused by {err.MESSAGE}")
                failed[chat] = err.MESSAGE
                # don't remove the chat for now
                # await self.db.update_one({"_id": data["_id"]}, {"$pull": {"chats": chat}})

        await ctx.respond(string)

        if failed:
            text = ""
            for key, err_msg in failed.items():
                text += f"failed to fban on chat {key} caused by {err_msg}\n\n"
            await ctx.respond(text, delete_after=20, mode="reply", reference=ctx.response)

        # send message to federation log
        if log := data.get("log"):
            await self.bot.client.send_message(log, string, disable_web_page_preview=True)

        return None

    async def cmd_unfban(self, ctx: command.Context, user: Optional[User] = None) -> str:
        """Unban a user on federation"""
        chat = ctx.chat
        if chat.type == "private":
            return await self.text(chat.id, "err-chat-groups")

        banner = ctx.msg.from_user
        data = await self.get_fed_bychat(chat.id)
        if not data:
            return await self.text(chat.id, "fed-no-fed-chat")

        if not self.is_fed_admin(data, banner.id):
            return await self.text(chat.id, "fed-admin-only")

        if not user:
            if ctx.args and not ctx.msg.reply_to_message:
                return await self.text(chat.id, "fed-no-ban-user")
            user = ctx.msg.reply_to_message.from_user

        if str(user.id) not in data.get("banned", {}).keys():
            return await self.text(chat.id, "fed-user-not-banned")

        await self.unfban_user(data["_id"], user.id)
        text = await self.text(
            chat.id,
            "fed-unban-info",
            data["name"],
            util.tg.mention(banner),
            util.tg.mention(user),
            user.id
        )
        for chat in data["chats"]:
            try:
                await self.bot.client.unban_chat_member(chat, user.id)
            except (BadRequest, Forbidden):
                pass

        if log := data.get("log"):
            await self.bot.client.send_message(log, text, disable_web_page_preview=True)

        return text

    @command.filters(aliases=["fstats"])
    async def cmd_fedstats(self, ctx: command.Context) -> str:
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

                return await self.text(chat.id, "fed-stat-not-banned")

            return await self.text(chat.id, "fed-not-found")

        reply_msg = ctx.msg.reply_to_message
        if len(ctx.args) == 1:  # <user_id>

            user_id = int(ctx.args[0])
            cursor = await self.check_fban(user_id)
            if not cursor:
                return await self.text(chat.id, "fed-stat-multi-not-banned")

            text = await self.text(chat.id, "fed-stat-multi")
            async for bans in cursor:
                text += "\n" + await self.text(
                    chat.id,
                    "fed-stat-multi-info",
                    bans["name"],
                    bans["_id"],
                    bans["banned"][str(user_id)]["reason"],
                )
                return text

            return await self.text(chat.id, "fed-stat-multi-not-banned")

        if reply_msg:
            user = reply_msg.from_user
        else:
            user = ctx.msg.from_user

        cursor = await self.check_fban(user.id)
        if cursor:
            text = await self.text(chat.id, "fed-stat-multi")
            async for bans in cursor:
                text += "\n" + await self.text(
                    chat.id,
                    "fed-stat-multi-info",
                    bans["name"],
                    bans["_id"],
                    bans["banned"][str(user.id)]["reason"],
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

        cursor = self.db.find({"admins": user.id})
        fed_list = await cursor.to_list()
        if fed_list:
            text = await self.text(chat.id, "fed-myfeds-admin") + "\n"
            for fed in fed_list:
                text += f"- `{fed['_id']}`: {fed['name']}\n"

            return text

        return await self.text(chat.id, "fed-myfeds-no-admin")

    async def cmd_setfedlog(self, ctx: command.Context, fid: Optional[str] = None) -> Optional[str]:
        chat = ctx.chat
        if chat.type == "channel":
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

        if chat.type in {"group", "supergroup"}:
            data = await self.get_fed_byowner(ctx.author.id)
            if not data:
                return await self.text(chat.id, "user-no-feds")

            ret, _ = await asyncio.gather(
                self.text(chat.id, "fed-log-set-group", data["name"]),
                self.db.update_one({"_id": data["_id"]}, {"$set": {"log": chat.id}}),
            )
            return ret

        return await self.text(chat.id, "err-chat-groups")

    async def cmd_unsetfedlog(self, ctx: command.Context) -> str:
        chat = ctx.chat
        user = ctx.msg.from_user
        if chat.type == "private":
            data = await self.get_fed_byowner(user.id)
            if not data:
                return await self.text(chat.id, "user-no-feds")

            ret, _ = await asyncio.gather(
                self.text(chat.id, "fed-log-unset", data["name"]),
                self.db.update_one({"_id": data["_id"]}, {"$set": {"log": None}}),
            )
            return ret

        return await self.text(chat.id, "err-chat-private")
