"""Bot Greetings"""
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
from html import escape
from typing import Any, ClassVar, MutableMapping, Optional, Tuple

from pyrogram.client import Client
from pyrogram.enums.parse_mode import ParseMode
from pyrogram.errors import ChannelPrivate, ChatWriteForbidden, MessageDeleteForbidden
from pyrogram.types import Chat, Message, User
from pyrogram.types.messages_and_media.message import Str

from anjani import command, filters, plugin, util


class Greeting(plugin.Plugin):
    name: ClassVar[str] = "Greetings"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("WELCOME")

    async def on_chat_action(self, message: Message) -> None:
        chat = message.chat
        reply_to = message.id
        if message.left_chat_member and message.left_chat_member.id == self.bot.uid:
            return

        # Clean service both for left member and new member if active
        if await self.clean_service(chat.id):
            try:
                await message.delete()
            except (MessageDeleteForbidden, ChannelPrivate):
                pass
            reply_to = 0

        if message.new_chat_members:
            return await self._member_join(message, reply_to)

        if message.left_chat_member:
            return await self._member_leave(message, reply_to)

    async def _member_leave(self, message: Message, reply_to: int) -> None:
        chat = message.chat
        if not await self.is_goodbye(chat.id):
            return

        left_member = message.left_chat_member
        text = await self.left_message(chat.id)
        if not text:
            text = await self.text(chat.id, "default-goodbye", noformat=True)

        formatted_text = await self._build_text(text, left_member, chat, self.bot.client)
        try:
            msg = await self.bot.client.send_message(
                chat.id,
                formatted_text,
                reply_to_message_id=reply_to,
            )
        except ChatWriteForbidden:
            return

        previous = await self.previous_goodbye(chat.id, msg.id)
        if previous:
            try:
                await self.bot.client.delete_messages(chat.id, previous)
            except MessageDeleteForbidden:
                pass

    async def _member_join(self, message: Message, reply_to: int) -> None:
        chat = message.chat
        if not await self.is_welcome(chat.id):
            return

        new_members = message.new_chat_members
        for new_member in new_members:
            try:
                if new_member.id == self.bot.uid:
                    await self.bot.client.send_message(
                        chat.id,
                        await self.text(chat.id, "bot-added"),
                        reply_to_message_id=reply_to,
                    )
                else:
                    text, button = await self.welc_message(chat.id)
                    if not text:
                        string = await self.text(chat.id, "default-welcome", noformat=True)
                    else:
                        string = text

                    formatted_text = await self._build_text(
                        string, new_member, chat, self.bot.client
                    )

                    if button:
                        button = util.tg.build_button(button)
                        msg = await self.bot.client.send_message(
                            chat.id,
                            formatted_text,
                            reply_to_message_id=reply_to,
                            reply_markup=button,
                        )
                    else:
                        msg = await self.bot.client.send_message(
                            chat.id,
                            formatted_text,
                            reply_to_message_id=reply_to,
                        )

                    previous = await self.previous_welcome(chat.id, msg.id)
                    if previous:
                        try:
                            await self.bot.client.delete_messages(chat.id, previous)
                        except MessageDeleteForbidden:
                            pass
            except ChatWriteForbidden:
                pass

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        welcome = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        return {self.name: welcome} if welcome else {}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True)

    @staticmethod
    async def _build_text(
        text: str, user: User, chat: Chat, client: Optional[Client] = None
    ) -> str:
        first_name = user.first_name or ""  # Ensure first name is not None
        last_name = user.last_name
        full_name = first_name + last_name if last_name else first_name
        try:
            count = await client.get_chat_members_count(chat.id) if client else "N/A"
        except ChannelPrivate:
            count = "N/A"

        return text.format(
            first=escape(first_name),
            last=escape(last_name) if last_name else "",
            fullname=escape(full_name),
            username=f"@{user.username}" if user.username else user.mention,
            mention=user.mention,
            count=count,
            chatname=escape(chat.title),
            id=user.id,
        )

    async def is_welcome(self, chat_id: int) -> bool:
        """Get chat welcome setting"""
        active = await self.db.find_one({"chat_id": chat_id}, {"should_welcome": 1})
        return active.get("should_welcome", True) if active else True

    async def is_goodbye(self, chat_id: int) -> bool:
        """Get chat welcome setting"""
        active = await self.db.find_one({"chat_id": chat_id}, {"should_goodbye": 1})
        return active.get("should_goodbye", True) if active else True

    async def welc_message(
        self, chat_id: int
    ) -> Tuple[Optional[str], Optional[Tuple[Tuple[str, str, bool]]]]:
        """Get chat welcome string"""
        message = await self.db.find_one({"chat_id": chat_id}, {"custom_welcome": 1, "button": 1})
        if message:
            return message.get("custom_welcome"), message.get("button")

        return await self.text(chat_id, "default-welcome", noformat=True), None

    async def left_message(self, chat_id: int) -> str:
        message = await self.db.find_one({"chat_id": chat_id}, {"custom_goodbye": 1})
        return (
            message.get(
                "custom_goodbye", await self.text(chat_id, "default-goodbye", noformat=True)
            )
            if message
            else await self.text(chat_id, "default-goodbye", noformat=True)
        )

    async def clean_service(self, chat_id: int) -> bool:
        """Fetch clean service setting"""
        clean = await self.db.find_one({"chat_id": chat_id}, {"clean_service": 1})
        if clean:
            return clean.get("clean_service", True)

        return False  # Defaults off

    async def set_custom_welcome(self, chat_id: int, text: Str) -> None:
        """Set custom welcome"""
        msg, button = util.tg.parse_button(text.markdown)
        await self.db.update_one(
            {"chat_id": chat_id},
            {"$set": {"custom_welcome": msg, "button": button}},
            upsert=True,
        )

    async def set_custom_goodbye(self, chat_id: int, text: str) -> None:
        """Set custom goodbye"""
        await self.db.update_one({"chat_id": chat_id}, {"$set": {"custom_goodbye": text}})

    async def del_custom_welcome(self, chat_id: int) -> None:
        """Delete custom welcome message"""
        await self.db.update_one(
            {"chat_id": chat_id}, {"$unset": {"custom_welcome": "", "button": ""}}
        )

    async def del_custom_goodbye(self, chat_id: int) -> None:
        """Delete custom goodbye message"""
        await self.db.update_one({"chat_id": chat_id}, {"$unset": {"custom_goodbye": ""}})

    async def greeting_setting(self, chat_id: int, key: str, value: bool) -> None:
        """Turn on/off greetings in chats"""
        if not value:
            await self.db.update_one({"chat_id": chat_id}, {"$set": {key: False}}, upsert=True)
        else:
            await self.db.update_one({"chat_id": chat_id}, {"$unset": {key: ""}}, upsert=True)

    async def previous_welcome(self, chat_id: int, msg_id: int) -> Optional[int]:
        """Save latest welcome msg_id and return previous msg_id"""
        data = await self.db.find_one_and_update(
            {"chat_id": chat_id}, {"$set": {"prev_welc": msg_id}}, upsert=True
        )
        return data.get("prev_welc", None) if data else None

    async def previous_goodbye(self, chat_id: int, msg_id: int) -> Optional[int]:
        data = await self.db.find_one_and_update(
            {"chat_id": chat_id}, {"$set": {"prev_gdby": msg_id}}, upsert=True
        )
        return data.get("prev_gdby", None) if data else None

    @command.filters(filters.admin_only)
    async def cmd_setwelcome(self, ctx: command.Context) -> str:
        """Set chat welcome message"""
        chat = ctx.chat
        if ctx.input:
            welc_text = Str(ctx.input).init(ctx.msg.entities[1:])
        elif ctx.msg.reply_to_message:
            welc_text = ctx.msg.reply_to_message.text or ctx.msg.reply_to_message.caption
        else:
            return await self.text(chat.id, "greetings-no-input")

        try:  # Try to build a text first to check message validity
            await self._build_text(welc_text or "", ctx.author, chat, self.bot.client)
        except (KeyError, ValueError) as e:
            return await self.text(chat.id, "err-msg-format-parsing", err=e)

        ret, _ = await asyncio.gather(
            self.text(chat.id, "cust-welcome-set"), self.set_custom_welcome(chat.id, welc_text)
        )
        return ret

    @command.filters(filters.admin_only)
    async def cmd_setgoodbye(self, ctx: command.Context) -> str:
        """Set chat goodbye message"""
        chat = ctx.chat
        if ctx.input:
            gby_text = Str(ctx.input).init(ctx.msg.entities[1:])
        elif ctx.msg.reply_to_message:
            gby_text = ctx.msg.reply_to_message.text or ctx.msg.reply_to_message.caption
        else:
            return await self.text(chat.id, "greetings-no-input")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "cust-goodbye-set"), self.set_custom_goodbye(chat.id, gby_text)
        )
        return ret

    @command.filters(filters.admin_only)
    async def cmd_resetwelcome(self, ctx: command.Context) -> str:
        """Reset saved welcome message"""
        chat = ctx.chat

        ret, _ = await asyncio.gather(
            self.text(chat.id, "reset-welcome"), self.del_custom_welcome(chat.id)
        )
        return ret

    @command.filters(filters.admin_only)
    async def cmd_resetgoodbye(self, ctx: command.Context) -> str:
        """Reset saved welcome message"""
        chat = ctx.chat

        ret, _ = await asyncio.gather(
            self.text(chat.id, "reset-goodbye"), self.del_custom_goodbye(chat.id)
        )
        return ret

    @command.filters(filters.admin_only)
    async def cmd_welcome(self, ctx: command.Context) -> Optional[str]:
        """View current welcome message"""
        chat = ctx.chat
        param = ctx.input.lower()
        noformat = param == "noformat"

        enabled = None
        if param in {"yes", "on", "1"}:
            enabled = True
        elif param in {"no", "off", "0"}:
            enabled = False
        elif param and not noformat:
            return await self.text(chat.id, "err-invalid-option")

        if enabled is not None:
            ret, _ = await asyncio.gather(
                self.text(chat.id, "welcome-set", "on" if enabled else "off"),
                self.greeting_setting(chat.id, "should_welcome", enabled),
            )
            return ret

        setting, (text, button), clean_service = await asyncio.gather(
            self.is_welcome(chat.id), self.welc_message(chat.id), self.clean_service(chat.id)
        )

        if text is None:
            text = ""
        else:
            text += "\n\n"

        if noformat:
            parse_mode = ParseMode.DISABLED
            if button:
                text += util.tg.revert_button(button)
            button = None
        else:
            parse_mode = ParseMode.MARKDOWN
            if button:
                button = util.tg.build_button(button)

        await ctx.respond(await self.text(chat.id, "view-welcome", setting, clean_service))
        await ctx.respond(
            text
            if text
            else (
                "Empty, custom welcome message haven't set yet."
                if not setting
                else "Default:\n\n" + await self.text(chat.id, "default-welcome", noformat=True)
            ),
            mode="reply",
            reply_markup=button,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
        return None

    @command.filters(filters.admin_only)
    async def cmd_goodbye(self, ctx: command.Context) -> Optional[str]:
        """View current goodbye message"""
        chat = ctx.chat
        param = ctx.input.lower()
        noformat = param == "noformat"

        enabled = None
        if param in {"yes", "on", "1"}:
            enabled = True
        elif param in {"no", "off", "0"}:
            enabled = False
        elif param and not noformat:
            return await self.text(chat.id, "err-invalid-option")

        if enabled is not None:
            ret, _ = await asyncio.gather(
                self.text(chat.id, "goodbye-set", "on" if enabled else "off"),
                self.greeting_setting(chat.id, "should_goodbye", enabled),
            )
            return ret

        setting, text, clean_service = await asyncio.gather(
            self.is_goodbye(chat.id), self.left_message(chat.id), self.clean_service(chat.id)
        )

        if noformat:
            parse_mode = ParseMode.DISABLED
        else:
            parse_mode = ParseMode.MARKDOWN

        await ctx.respond(await self.text(chat.id, "view-goodbye", setting, clean_service))
        await ctx.respond(
            text,
            mode="reply",
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
        return None

    @command.filters(filters.admin_only)
    async def cmd_cleanservice(self, ctx: command.Context, active: Optional[bool] = None) -> str:
        """Clean service message on new members"""
        chat = ctx.chat

        if active is None:
            return await self.text(chat.id, "err-invalid-option")

        ret, _ = await asyncio.gather(
            self.text(chat.id, "clean-serv-set", "on" if active else "off"),
            self.greeting_setting(chat.id, "clean_service", active),
        )
        return ret
