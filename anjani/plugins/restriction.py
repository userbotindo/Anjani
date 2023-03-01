""" Restriction Plugin. """
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
from typing import Any, ClassVar, MutableMapping, Optional, Union

from bson.objectid import ObjectId
from pyrogram.enums.chat_member_status import ChatMemberStatus
from pyrogram.errors import BadRequest, PeerIdInvalid, UserNotParticipant
from pyrogram.types import (
    CallbackQuery,
    Chat,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)

from anjani import command, filters, listener, plugin, util


class Restrictions(plugin.Plugin):
    name: ClassVar[str] = "Restriction"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("CHATS")

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        data = await self.db.find_one(
            {"chat_id": chat_id, "warn_list": {"$exists": True}}, {"_id": 0, "warn_list": 1}
        )
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
        """Remove warn callback data"""
        chat = query.message.chat
        user = query.matches[0].group(1)
        uid = query.matches[0].group(2)

        try:
            invoker = await chat.get_member(query.from_user.id)
        except UserNotParticipant:
            return await query.answer(
                await self.get_text(chat.id, "error-no-rights"), show_alert=True
            )

        if not invoker.privileges or not invoker.privileges.can_restrict_members:
            return await query.answer(await self.get_text(chat.id, "warn-keyboard-not-admins"))

        chat_data = await self.db.find_one(
            {"chat_id": chat.id, "warn_list": {"$exists": True}}, {"warn_list": 1}
        )
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
                    chat.id,
                    "warn-removed",
                    query.from_user.mention,
                    target.mention,
                )
            ),
        )

    @command.filters(filters.can_restrict)
    async def cmd_kick(
        self, ctx: command.Context, target: Union[User, Chat, None] = None, *, reason: str = ""
    ) -> str:
        """Kick chat member"""
        chat = ctx.chat
        reply_msg = ctx.msg.reply_to_message

        if not target:
            if ctx.args and not reply_msg:
                return await self.text(chat.id, "err-peer-invalid")

            if not reply_msg or not (reply_msg.from_user or reply_msg.sender_chat):
                return await self.text(chat.id, "no-kick-user")

            target = reply_msg.from_user or reply_msg.sender_chat
            reason = ctx.input

        try:
            if isinstance(target, User) and util.tg.is_staff_or_admin(
                await chat.get_member(target.id)
            ):
                return await self.text(chat.id, "admin-kick")
        except UserNotParticipant:
            if util.tg.is_staff(target.id):
                return await self.text(chat.id, "admin-kick")

        await self.bot.client.ban_chat_member(chat.id, target.id)

        async def unban():
            await asyncio.sleep(5)
            await self.bot.client.unban_chat_member(chat.id, target.id)

        asyncio.create_task(unban())

        ret = await self.text(
            chat.id, "kick-done", target.first_name if isinstance(target, User) else target.title
        )
        if reason:
            ret += await self.text(chat.id, "kick-reason", reason)

        return ret

    async def _ban(
        self,
        ctx: command.Context,
        target: Union[User, Chat, None] = None,
        reason: str = "",
        silent: bool = False,
    ) -> Optional[str]:
        chat = ctx.chat
        reply_msg = ctx.msg.reply_to_message

        if not target:
            if ctx.args and not reply_msg:
                return await self.text(chat.id, "err-peer-invalid")

            if not reply_msg or not (reply_msg.from_user or reply_msg.sender_chat):
                return await self.text(chat.id, "no-ban-user")

            target = reply_msg.from_user or reply_msg.sender_chat
            reason = ctx.input

        try:
            if isinstance(target, User) and util.tg.is_staff_or_admin(
                await chat.get_member(target.id)
            ):
                return await self.text(chat.id, "admin-ban")
        except UserNotParticipant:
            # Not a participant in the chat (replying from channel discussion)
            if util.tg.is_staff(target.id):
                return await self.text(chat.id, "admin-ban")

        ret, _ = await asyncio.gather(
            self.text(
                chat.id, "ban-done", target.first_name if isinstance(target, User) else target.title
            ),
            chat.ban_member(target.id),
        )
        if reason:
            ret += await self.text(chat.id, "ban-reason", reason)

        return ret if not silent else None

    @command.filters(filters.can_restrict)
    async def cmd_ban(
        self, ctx: command.Context, target: Union[User, Chat, None] = None, *, reason: str = ""
    ) -> str:
        """Ban chat member"""
        ret = await self._ban(ctx, target, reason)
        if not ret:
            raise ValueError

        return ret

    @command.filters(filters.can_restrict)
    async def cmd_sban(self, ctx: command.Context, target: Union[User, Chat, None] = None) -> None:
        """Silently ban chat member"""
        ret = await self._ban(ctx, target, silent=True)
        if ret:
            await ctx.respond(ret, delete_after=1)

        await ctx.msg.delete()

    @command.filters(filters.can_restrict)
    async def cmd_unban(self, ctx: command.Context, user: Union[User, Chat, None] = None) -> str:
        """Unban chat member"""
        chat = ctx.chat

        if not user:
            if ctx.input:
                return await self.text(chat.id, "err-peer-invalid")

            if not ctx.msg.reply_to_message:
                return await self.text(chat.id, "unban-no-user")

            user = ctx.msg.reply_to_message.from_user or ctx.msg.reply_to_message.sender_chat

        try:
            await chat.unban_member(user.id)
        except (BadRequest, PeerIdInvalid) as e:
            if isinstance(e.value, str) and "PARTICIPANT_ID_INVALID" in e.value:
                return await self.text(chat.id, "err-invalid-pid")

            if isinstance(e, PeerIdInvalid):
                return await self.text(chat.id, "err-peer-invalid")

            raise e from BadRequest

        return await self.text(
            chat.id, "unban-done", user.first_name if isinstance(user, User) else user.title
        )

    @command.filters(filters.can_restrict)
    async def cmd_warn(
        self, ctx: command.Context, user: Optional[User] = None, *, reason: str = ""
    ) -> Optional[str]:
        """Warn command chat member"""
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
        if target.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
            return await ctx.get_text("rmwarn-admin")

        threshold = 3
        warns: Optional[int] = None
        chat_data = await self.db.find_one(
            {"chat_id": chat.id, "warn_list": {"$exists": True}},
            {"warn_list": 1, "warn_threshold": 1},
        )
        if chat_data:  # Get threshold and existing warns from chat data
            threshold = chat_data.get("warn_threshold", 3)
            try:
                warns = len(chat_data["warn_list"][str(user.id)])
            except KeyError:
                pass

        uid = str(ObjectId())
        reason = reason or await ctx.get_text("warn-default-reason")
        keyboard = [
            [
                InlineKeyboardButton(
                    await ctx.get_text("warn-keyboard-text"),
                    callback_data=f"rm_warn_{user.id}_{uid}",
                )
            ]
        ]
        await asyncio.gather(
            self.db.update_one(
                {"chat_id": chat.id}, {"$set": {f"warn_list.{user.id}.{uid}": reason}}, upsert=True
            ),
            ctx.respond(
                await self.get_text(
                    chat.id,
                    "warn-message",
                    user.mention,
                    1 if warns is None else warns + 1,
                    threshold,
                    reason,
                ),
                reply_markup=InlineKeyboardMarkup(keyboard),
            ),
        )

        if warns is not None and warns + 1 >= threshold:
            ret, _ = await asyncio.gather(
                ctx.get_text("warn-user-max", user.mention), chat.ban_member(user.id)
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
        if target.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
            return await ctx.get_text("rmwarn-admin")

        chat_data = await self.db.find_one(
            {"chat_id": chat.id, "warn_list": {"$exists": True}},
            {"warn_list": 1, "warn_threshold": 1},
        )
        if not chat_data:
            return await ctx.get_text("warn-no-data", user.mention)
        threshold = chat_data.get("warn_threshold", 3)

        try:
            warns_list = chat_data["warn_list"][str(user.id)]
        except KeyError:
            return await ctx.get_text("warn-no-data", user.mention)
        else:
            warns = len(warns_list)
            if warns == 0:
                return await ctx.get_text("warn-no-data", user.mention)

        return await self.get_text(
            chat.id,
            "warn-message-list",
            user.mention,
            warns,
            threshold,
            "\n".join(f"  • __{reason}__" for reason in warns_list.values()),
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
    async def cmd_rmwarn(self, ctx: command.Context, user: Optional[User] = None) -> Optional[str]:
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
        if target.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
            return await ctx.get_text("rmwarn-admin")

        chat_data = await self.db.find_one(
            {"chat_id": chat.id, "warn_list": {"$exists": True}}, {"warn_list": 1}
        )
        if not chat_data:
            return await ctx.get_text("warn-no-data", user.mention)

        try:
            warns_list = chat_data["warn_list"][str(user.id)]
        except KeyError:
            return await ctx.get_text("warn-no-data", user.mention)

        try:
            ret, _ = await asyncio.gather(
                self.get_text(chat.id, "rmwarn-done", user.mention),
                self.db.update_one(
                    {"chat_id": chat.id},
                    {"$unset": {f"warn_list.{user.id}.{list(warns_list.keys())[-1]}": ""}},
                ),
            )
        except IndexError:
            return await ctx.get_text("warn-no-data", user.mention)

        return ret
