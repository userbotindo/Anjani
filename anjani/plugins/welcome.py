"""Bot Greetings"""
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
from html import escape
from typing import Any, ClassVar, MutableMapping, Optional, Tuple, Union

from pyrogram.errors import MessageDeleteForbidden
from pyrogram.types.messages_and_media.message import Message, Str

from anjani import command, plugin, util
from anjani.custom_filter import admin_only


class Greeting(plugin.Plugin):
    name: ClassVar[str] = "Greetings"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("WELCOME")

    async def on_chat_action(self, message: Message) -> None:
        chat = message.chat
        new_members = message.new_chat_members
        reply_to = message.message_id

        # Clean service both for left member and new member if active
        if await self.clean_service(chat.id):
            try:
                await message.delete()
            except MessageDeleteForbidden:
                pass
            reply_to = None
    
        if message.left_chat_member or not await self.is_active(chat.id):
            return

        for new_member in new_members:
            if new_member.id == self.bot.uid:
                await self.bot.client.send_message(
                    chat.id,
                    await self.text(chat.id, "bot-added"),
                    reply_to_message_id=reply_to,
                )
            else:
                text, button = await self.message(chat.id)
                if not text:
                    text = await self.text(chat.id, "default-welcome", noformat=True)

                first_name = new_member.first_name
                last_name = new_member.last_name
                full_name = first_name + last_name if last_name else first_name
                formatted_text = text.format(
                    first=escape(first_name),
                    last=escape(last_name) if last_name else "",
                    fullname=escape(full_name),
                    username=new_member.username,
                    mention=new_member.mention,
                    count=chat.members_count,
                    chatname=escape(chat.title),
                    id=new_member.id,
                )

                if button:
                    button = util.tg.build_button(button)

                msg = await self.bot.client.send_message(
                    chat.id,
                    formatted_text,
                    reply_to_message_id=reply_to,
                    reply_markup=button,
                )

                previous = await self.previous_welcome(chat.id, msg.message_id)
                if previous:
                    try:
                        await self.bot.client.delete_messages(chat.id, previous)
                    except MessageDeleteForbidden:
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
        if not welcome:
            return {}

        return {self.name: welcome}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id},
                                 {"$set": data[self.name]},
                                 upsert=True)

    async def is_active(self, chat_id: int) -> bool:
        """Get chat welcome setting"""
        active = await self.db.find_one({"chat_id": chat_id})
        return active["should_welcome"] if active else False

    async def message(self, chat_id: int) -> Tuple[Optional[str],
                                                   Optional[Tuple[Tuple[str, str, bool]]]]:
        """Get chat welcome string"""
        message = await self.db.find_one({"chat_id": chat_id})
        if message:
            return message.get("custom_welcome"), message.get("button")

        return await self.text(chat_id, "default-welcome", noformat=True), None

    async def clean_service(self, chat_id: int) -> bool:
        """Fetch clean service setting"""
        clean = await self.db.find_one({"chat_id": chat_id})
        if clean:
            return clean.get("clean_service", False)

        return False

    async def set_custom_welcome(self, chat_id: int, text: Str) -> None:
        """Set custome welcome"""
        msg, button = util.tg.parse_button(text.markdown)
        await self.db.update_one(
            {"chat_id": chat_id},
            {"$set": {"custom_welcome": msg, "button": button}},
            upsert=True,
        )

    async def del_custom_welcome(self, chat_id: int) -> None:
        """Delete custom welcome msg"""
        await self.db.update_one({"chat_id": chat_id},
                                 {"$unset": {"custom_welcome": "",
                                 "button": ""}})

    async def cleanservice_update(self, chat_id: int, value: bool) -> None:
        """Clean service db"""
        await self.db.update_one({"chat_id": chat_id},
                                 {"$set": {"clean_service": value}},
                                 upsert=True)

    async def setting(self, chat_id: int, value: bool) -> None:
        """Turn on/off welcome in chats"""
        await self.db.update_one({"chat_id": chat_id},
                                 {"$set": {"should_welcome": value}},
                                 upsert=True)

    async def previous_welcome(self, chat_id, msg_id: int) -> Union[int, bool]:
        """Save latest welcome msg_id and return previous msg_id"""
        data = await self.db.find_one_and_update(
            {"chat_id": chat_id}, {"$set": {"prev_welc": msg_id}}, upsert=True
        )
        if data:
            return data.get("prev_welc", False)

        return False

    @command.filters(admin_only)
    async def cmd_setwelcome(self, ctx: command.Context) -> str:
        """Set chat welcome message"""
        chat = ctx.chat

        if not ctx.msg.reply_to_message:
            return await self.text(chat.id, "error-reply-to-message")

        reply_msg = ctx.msg.reply_to_message
        ret, _= await asyncio.gather(self.text(chat.id, "cust-welcome-set"),
                                     self.set_custom_welcome(chat.id, reply_msg.text))
        return ret

    @command.filters(admin_only)
    async def cmd_resetwelcome(self, ctx: command.Context) -> str:
        """Reset saved welcome message"""
        chat = ctx.chat

        ret, _ = await asyncio.gather(self.text(chat.id, "reset-welcome"),
                                      self.del_custom_welcome(chat.id))
        return ret

    @command.filters(admin_only)
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
                self.setting(chat.id, enabled)
            )
            return ret

        setting, (text, button), clean_service = await asyncio.gather(
            self.is_active(chat.id),
            self.message(chat.id),
            self.clean_service(chat.id)
        )

        if text is None:
            text = ""
        else:
            text += "\n\n"

        if noformat:
            parse_mode = None
            if button:
                text += util.tg.revert_button(button)
            button = None
        else:
            parse_mode = "markdown"
            if button:
                button = util.tg.build_button(button)

        await ctx.respond(await self.text(chat.id, "view-welcome", setting, clean_service))
        await ctx.respond(
            text if text else (
                "Empty, custom welcome message haven't set yet."
                if not setting else "Default:\n\n" + await self.text(
                    chat.id,
                    "default-welcome",
                    noformat=True
                )
            ),
            mode="reply",
            reply_markup=button,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )

    @command.filters(admin_only)
    async def cmd_cleanservice(self, ctx: command.Context) -> str:
        """Clean service message on new members"""
        chat = ctx.chat
        param = ctx.input

        if param in {"yes", "on", "1"}:
            active = True
        elif param in {"no", "off", "0"}:
            active = False
        elif param:
            return await self.text(chat.id, "err-invalid-option")
        else:
            return "Usage is on/yes or off/no"

        ret, _ = await asyncio.gather(
            self.text(chat.id, "clean-serv-set", "on" if active else "off"),
            self.cleanservice_update(chat.id, active)
        )
        return ret
