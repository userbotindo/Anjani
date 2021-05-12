"""Notes Plugins"""
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
from functools import partial
from typing import Any, ClassVar, Dict, List, Match, Union

from motor.motor_asyncio import AsyncIOMotorCollection
from pyrogram import filters
from pyrogram.types import Message

from anjani_bot import listener, plugin
from anjani_bot.utils import MessageParser, SendFormating, Types


class NotesBase(SendFormating, MessageParser):
    async def __on_load__(self):
        self.notes_db = self.bot.get_collection("NOTES")
        self.lock = asyncio.Lock()
        super().__init__()

    async def __migrate__(self, old_chat, new_chat):
        async with self.lock:
            await self.notes_db.update_one(
                {"chat_id": old_chat},
                {"$set": {"chat_id": new_chat}},
            )

    async def __backup__(self, chat_id, data=None):
        if data and data.get(self.name):
            async with self.lock:
                await self.notes_db.update_one(
                    {"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True
                )
        elif not data:
            return await self.notes_db.find_one({"chat_id": chat_id}, {"_id": False})

    def _reply_note(self, match: Match[str]) -> str:
        async def get_data(key):
            data = self.cache.get("notes")
            return data.get(key)

        fut = asyncio.run_coroutine_threadsafe(get_data(match), self.bot.loop)
        data: Dict[str, Any] = fut.result()
        if data is not None:
            return data
        return None

    async def get_note(self, message: Message, name: str, noformat: bool = False) -> None:
        """Get note data and send based on types."""
        chat_id = message.chat.id
        reply_to = message.message_id

        self.cache = await self.notes_db.find_one({"chat_id": chat_id})
        if self.cache is None:
            return

        note = await self.bot.loop.run_in_executor(
            self.bot.client.executor, partial(self._reply_note, name)
        )

        if note:
            button = note.get("button", None)
            if noformat:
                parse_mode = None
                btn_text = "\n\n" + self.revert_button(button)
                keyb = None
            else:
                parse_mode = "markdown"
                keyb = self.build_button(button)
                btn_text = ""

            if note.get("type") in (Types.TEXT, Types.BUTTON_TEXT):
                await self.send_format[note.get("type")](
                    chat_id,
                    note.get("text") + btn_text,
                    disable_web_page_preview=True,
                    reply_to_message_id=reply_to,
                    reply_markup=keyb,
                    parse_mode=parse_mode,
                )
            elif note.get("type") == Types.STICKER:
                await self.send_format[note.get("type")](
                    chat_id,
                    note.get("content"),
                    reply_to_message_id=reply_to,
                )
            else:
                await self.send_format[note.get("type")](
                    chat_id,
                    str(note.get("content")),
                    caption=note.get("text") + btn_text,
                    reply_to_message_id=reply_to,
                    reply_markup=keyb,
                    parse_mode=parse_mode,
                )

    async def add_note(
        self,
        chat_title: str,
        chat_id: str,
        note_name: str,
        text: str,
        msg_type: Types,
        content: Union[str, None],
        buttons: List,
    ) -> None:
        """Add new chat note"""
        async with self.lock:
            await self.notes_db.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {
                        "chat_name": chat_title,
                        f"notes.{note_name}": {
                            "text": text,
                            "type": msg_type,
                            "content": content,
                            "button": buttons,
                        },
                    }
                },
                upsert=True,
            )

    async def del_note(self, chat_id: str, name: str):
        """Delete db note data"""
        async with self.lock:
            await self.notes_db.update_one(
                {"chat_id": chat_id},
                {"$unset": {f"notes.{name}": ""}},
            )


class NotesPlugin(plugin.Plugin, NotesBase):
    name: ClassVar[str] = "Notes"
    helpable: ClassVar[bool] = True
    notes_db: AsyncIOMotorCollection
    lock: asyncio.Lock
    cache: Dict[str, Any]

    @listener.on("get")
    async def get_notes_cmd(self, message):
        """Notes command trigger."""
        args = message.command
        if len(args) >= 2 and args[1].lower() == "noformat":
            await self.get_note(message, args[0], noformat=True)
        elif len(args) >= 1:
            await self.get_note(message, args[0])

    @listener.on(filters=filters.regex(r"^#[^\s]+"), update="message")
    async def get_notes_hash(self, message):
        """Notes hashtag trigger."""
        msg = message.text
        if not msg:
            return

        args = msg.split()
        if len(args) >= 2 and args[1].lower() == "noformat":
            await self.get_note(message, args[0][1:], noformat=True)
        elif len(args) >= 1:
            await self.get_note(message, args[0][1:])

    @listener.on("save", admin_only=True)
    async def cmd_note(self, message: Message) -> str:
        """Save notes."""
        chat_id = message.chat.id
        if len(message.command) < 2 and not message.reply_to_message:
            return await message.reply_text(await self.bot.text(chat_id, "notes-invalid-args"))

        name = message.command[0]
        text, msg_type, content, buttons = self.get_msg_type(message)
        await self.add_note(
            message.chat.title,
            chat_id,
            name,
            text,
            msg_type,
            content,
            buttons,
        )
        await message.reply_text(await self.bot.text(chat_id, "note-saved", name))

    @listener.on("notes")
    async def cmd_notelist(self, message) -> str:
        """View chat notes."""
        chat_id = message.chat.id
        check = await self.notes_db.find_one({"chat_id": chat_id})

        if not check or not check.get("notes"):
            return await message.reply_text(await self.bot.text(chat_id, "no-notes"))

        notes = await self.bot.text(chat_id, "note-list", message.chat.title)
        for key in check.get("notes").keys():
            notes += f"× `{key}`\n"
        return await message.reply_text(notes)

    @listener.on(["clear", "delnote"], admin_only=True)
    async def cmd_delnote(self, message):
        """Delete chat note."""
        chat_id = message.chat.id
        if not message.command:
            return await message.reply_text(await self.bot.text(chat_id, "notes-del-noargs"))
        name = message.command[0]

        check = await self.notes_db.find_one({"chat_id": chat_id})
        if check is None:
            return await message.reply_text(await self.bot.text(chat_id, "no-notes"))
        if check is not None and not check.get("notes").get(name):
            return await message.reply_text(await self.bot.text(chat_id, "notes-not-exist"))

        await self.del_note(chat_id, name)
        return await message.reply_text(await self.bot.text(chat_id, "notes-deleted", name))
