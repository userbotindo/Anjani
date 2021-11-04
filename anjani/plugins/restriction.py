""" Restriction Plugin. """
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
from typing import Any, ClassVar, MutableMapping, Optional

import bson
from pyrogram.errors import PeerIdInvalid, UserNotParticipant
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, User

from anjani import command, filters, listener, plugin, util


class Restrictions(plugin.Plugin):
    name: ClassVar[str] = "Restriction"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("CHATS")

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        data = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        try:
            return {self.name: data["warn_list"]} if data else {}
        except KeyError:
            return {} 

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one(
            {"chat_id": chat_id}, {"$set": {"warn_list": data[self.name]}}, upsert=True
        )

    @listener.filters(filters.regex(r"^rm_warn_(\d+)_(.*)"))
    async def on_callback_query(self, query: CallbackQuery) -> None:
        chat = query.message.chat
        user = query.matches[0].group(1)
        uid = query.matches[0].group(2)
        invoker = await chat.get_member(query.from_user.id)
        if not invoker.can_restrict_members:
            return await query.answer(await self.get_text(chat.id, "warn-keyboard-not-admins"))

        chat_data = await self.db.find_one({"chat_id": chat.id})
        if not chat_data:
            return

        warn_list = chat_data.get("warn_list", {})
        try:
            warns = len(warn_list[user])
        except KeyError:
            warns = 0

        if user not in warn_list or warns == 0:
            await query.message.edit(await self.get_text(chat.id, "warn-keyboard-removed"))
            return

        target = await self.bot.client.get_users(int(user))
        if isinstance(target, list):
            target = target[0]

        await asyncio.gather(
            self.db.update_one(
                {"chat_id": chat.id},
                {"$unset": {f"warn_list.{user}.{uid}": ""}},
            ),
            query.message.edit(
                await self.get_text(
                    chat.id, "warn-removed",
                    util.tg.mention(query.from_user), util.tg.mention(target),
                )
            )
        )

    async def kick(self, user: int, chat: int) -> None:
        await self.bot.client.kick_chat_member(chat, user)
        await asyncio.sleep(1)
        await self.bot.client.unban_chat_member(chat, user)

    @command.filters(filters.can_restrict)
    async def cmd_kick(
        self, ctx: command.Context, user: Optional[User] = None, *, reason: str = ""
    ) -> str:
        """Kick chat member"""
        chat = ctx.chat
        reply_msg = ctx.msg.reply_to_message

        if not user:
            if ctx.args and not reply_msg:
                return await self.text(chat.id, "err-peer-invalid")

            if not reply_msg:
                return await self.text(chat.id, "no-kick-user")

            user = reply_msg.from_user
            reason = ctx.input

        try:
            target = await chat.get_member(user.id)
            if util.tg.is_staff_or_admin(target):
                return await self.text(chat.id, "admin-kick")
        except UserNotParticipant:
            return await self.text(chat.id, "err-not-participant")

        await self.kick(user.id, chat.id)

        ret = await self.text(chat.id, "kick-done", user.first_name)
        if reason:
            ret += await self.text(chat.id, "kick-reason", reason)
        return ret

    @command.filters(filters.can_restrict)
    async def cmd_ban(
        self, ctx: command.Context, user: Optional[User] = None, *, reason: str = ""
    ) -> str:
        """Ban chat member"""
        chat = ctx.chat
        reply_msg = ctx.msg.reply_to_message

        if not user:
            if ctx.args and not reply_msg:
                return await self.text(chat.id, "err-peer-invalid")

            if not reply_msg:
                return await self.text(chat.id, "no-ban-user")

            user = reply_msg.from_user
            reason = ctx.input

        try:
            target = await chat.get_member(user.id)
            if util.tg.is_staff_or_admin(target):
                return await self.text(chat.id, "admin-ban")
        except UserNotParticipant:
            return await self.text(chat.id, "err-not-participant")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "ban-done", user.first_name), chat.kick_member(user.id)
        )
        if reason:
            ret += await self.text(chat.id, "ban-reason", reason)

        return ret

    @command.filters(filters.can_restrict)
    async def cmd_unban(self, ctx: command.Context, user: Optional[User] = None) -> str:
        """Unban chat member"""
        chat = ctx.chat

        if not user:
            if ctx.input:
                return await self.text(chat.id, "err-peer-invalid")

            if not ctx.msg.reply_to_message:
                return await self.text(chat.id, "unban-no-user")

            user = ctx.msg.reply_to_message.from_user

        try:
            await chat.unban_member(user.id)
        except PeerIdInvalid:
            return await self.text(chat.id, "err-peer-invalid")

        return await self.text(chat.id, "unban-done", user.first_name)

    @command.filters(filters.can_restrict)
    async def cmd_warn(
        self, ctx: command.Context, user: Optional[User] = None, *, reason: str = ""
    ) -> Optional[str]:
        chat = ctx.chat
        reply_msg = ctx.msg.reply_to_message
        if not user:
            if ctx.input and not reply_msg:
                return await ctx.get_text("err-peer-invalid")

            if not reply_msg:
                return await ctx.get_text("warn-no-user")

            reason = ctx.input
            user = reply_msg.from_user

        if user.id == self.bot.uid:
            return await ctx.get_text("error-its-myself")

        target = await chat.get_member(user.id)
        if target.status in {"administrator", "creator"}:
            return await ctx.get_text("rmwarn-admin")
        
        threshold = 3
        warns: Optional[int] = None
        chat_data = await self.db.find_one({"chat_id": chat.id})
        if chat_data:  # Get threshold and existing warns from chat data
            threshold = chat_data.get("warn_threshold", 3)
            try:
                warns = len(chat_data["warn_list"][str(user.id)])
            except KeyError:
                pass

        uid = str(bson.ObjectId())
        reason = reason or await ctx.get_text("warn-default-reason")
        keyboard = [
            [
                InlineKeyboardButton(
                    await ctx.get_text("warn-keyboard-text"),
                    callback_data=f"rm_warn_{user.id}_{uid}"
                )
            ]
        ]
        await asyncio.gather(
            self.db.update_one(
                {"chat_id": chat.id},
                {"$set": {f"warn_list.{user.id}.{uid}": reason}},
                upsert=True
            ),
            ctx.respond(
                await self.get_text(
                    chat.id,
                    "warn-message",
                    util.tg.mention(user),
                    1 if warns is None else warns + 1,
                    threshold,
                    reason,
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        )

        if warns is not None and warns + 1 >= threshold:
            ret, _ = await asyncio.gather(
                ctx.get_text("warn-user-max", util.tg.mention(user)),
                chat.kick_member(user.id)
            )
            return ret

        return None

    @command.filters(filters.group)
    async def cmd_warns(self, ctx: command.Context) -> str:
        """Get warns of a user"""
        reply_msg = ctx.msg.reply_to_message
        chat, user = ctx.chat, reply_msg.from_user if reply_msg else ctx.author
        threshold = 3

        if user.id == self.bot.uid:
            return await ctx.get_text("error-its-myself")

        target = await chat.get_member(user.id)
        if target.status in {"administrator", "creator"}:
            return await ctx.get_text("rmwarn-admin")

        chat_data = await self.db.find_one({"chat_id": chat.id})
        if not chat_data:
            return await ctx.get_text("warn-no-data", util.tg.mention(user))
        else:
            threshold = chat_data.get("warn_threshold", 3)

        try:
            warns_list = chat_data["warn_list"][str(user.id)]
        except KeyError:
            return await ctx.get_text("warn-no-data", util.tg.mention(user))
        else:
            warns = len(warns_list)
            if warns == 0:
                return await ctx.get_text("warn-no-data", util.tg.mention(user))

        return await self.get_text(
            chat.id,
            "warn-message-list",
            util.tg.mention(user),
            warns,
            threshold,
            "\n".join(f"  • __{reason}__" for reason in warns_list.values())
        )

    @command.filters(filters.admin_only, aliases={"warnlim"})
    async def cmd_warnlimit(self, ctx: command.Context, limit: int) -> Optional[str]:
        """Set warn limit"""
        chat = ctx.chat
        if limit is None:
            return await ctx.get_text("warn-limit-no-input")

        if not isinstance(limit, int):
            return await ctx.get_text("warn-limit-invalid-input")

        if limit <= 0:
            return await ctx.get_text("warn-limit-invalid-input")

        ret, _ = await asyncio.gather(
            ctx.get_text("warn-limit-done", limit),
            self.db.update_one({"chat_id": chat.id}, {"$set": {"warn_threshold": limit}}),
        )
        return ret

    @command.filters(filters.can_restrict, aliases={"removewarn"})
    async def cmd_rmwarn(
        self, ctx: command.Context, user: Optional[User] = None
    ) -> Optional[str]:
        """Remove a warn"""
        chat = ctx.chat
        reply_msg = ctx.msg.reply_to_message

        if not user:
            if ctx.input and not reply_msg:
                return await ctx.get_text("err-peer-invalid")

            if not reply_msg:
                return await ctx.get_text("rmwarn-no-user")

            user = reply_msg.from_user

        if user.id == self.bot.uid:
            return await ctx.get_text("error-its-myself")

        target = await chat.get_member(user.id)
        if target.status in {"administrator", "creator"}:
            return await ctx.get_text("rmwarn-admin")

        chat_data = await self.db.find_one({"chat_id": chat.id})
        if not chat_data:
            return await ctx.get_text("warn-no-data", util.tg.mention(user))

        try:
            warns_list = chat_data["warn_list"][str(user.id)]
        except KeyError:
            return await ctx.get_text("warn-no-data", util.tg.mention(user))

        ret, _ = await asyncio.gather(
            self.get_text(
                chat.id,
                "rmwarn-done",
                util.tg.mention(user)
            ),
            self.db.update_one(
                {"chat_id": chat.id},
                {"$unset": {f"warn_list.{user.id}.{list(warns_list.keys())[-1]}": ""}},
            )
        )
        return ret
