""" Filters plugin. """
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
from typing import (
    Any,
    Callable,
    ClassVar,
    Coroutine,
    MutableMapping,
    Optional,
    Set,
    Tuple,
)

from pyrogram.errors import MediaEmpty, MessageEmpty
from pyrogram.types import Message

from anjani import command, filters, listener, plugin, util
from anjani.util.tg import Types, build_button, get_message_info


class Filters(plugin.Plugin):
    name: ClassVar[str] = "Filters"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection
    trigger: MutableMapping[int, Set[str]] = {}
    SEND: MutableMapping[int, Callable[..., Coroutine[Any, Any, Optional[Message]]]]

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("FILTERS")
        self.SEND = {
            Types.TEXT.value: self.bot.client.send_message,
            Types.BUTTON_TEXT.value: self.bot.client.send_message,
            Types.DOCUMENT.value: self.bot.client.send_document,
            Types.PHOTO.value: self.bot.client.send_photo,
            Types.VIDEO.value: self.bot.client.send_video,
            Types.STICKER.value: self.bot.client.send_sticker,
            Types.AUDIO.value: self.bot.client.send_audio,
            Types.VOICE.value: self.bot.client.send_voice,
            Types.VIDEO_NOTE.value: self.bot.client.send_video_note,
            Types.ANIMATION.value: self.bot.client.send_animation,
        }

    async def on_start(self, _: int) -> None:
        async for chat in self.db.find({}):
            self.trigger[chat["chat_id"]] = set(chat["trigger"].keys())

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        data = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        return {self.name: data} if data else {}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id}, {"$set": {data[self.name]}}, upsert=True)

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    @listener.priority(95)
    async def on_message(self, message: Message) -> None:
        if message.outgoing:
            return

        chat = message.chat
        text = message.text or message.caption

        if not (text or chat):
            return

        chat_trigger = self.trigger.get(chat.id, [])
        if not chat_trigger:
            return

        await self.reply_filter(message, set(chat_trigger), text)

    async def reply_filter(self, message: Message, trigger: Set[str], text: str):
        if not text or text.startswith("/filter") or text.startswith("/stop"):
            return  # Igonore when command triggered
        for i in trigger:
            pattern = r"( |^|[^\w])" + re.escape(i) + r"( |$|[^\w])"
            if re.search(pattern, text, flags=re.IGNORECASE):
                filt = await self.get_filter(message.chat.id, i)
                if not filt:
                    return

                # This checks data for old filters schema
                # TODO: deprecate old schema on v3
                if isinstance(filt, str):
                    await message.reply_text(filt)
                else:
                    reply_to = (
                        message.reply_to_message.id if message.reply_to_message else message.id
                    )
                    types: int = filt["type"]
                    button = filt.get("button", None)
                    if button:
                        keyb = build_button(button)
                    else:
                        keyb = button

                    try:
                        if types in {Types.TEXT, Types.BUTTON_TEXT}:
                            await self.SEND[types](
                                message.chat.id,
                                filt["text"],
                                reply_to_message_id=reply_to,
                                reply_markup=keyb,
                            )
                        elif types in {Types.STICKER, Types.ANIMATION}:
                            await self.SEND[types](
                                message.chat.id,
                                filt["content"],
                                reply_to_message_id=reply_to,
                            )
                        else:
                            await self.SEND[types](
                                message.chat.id,
                                filt["content"],
                                caption=filt["text"],
                                reply_to_message_id=reply_to,
                                reply_markup=keyb,
                            )
                    except MediaEmpty:
                        await self.bot.client.send_message(
                            message.chat.id, await self.text(message.chat.id, "notes-expired")
                        )
                    except MessageEmpty:
                        self.log.warning(
                            "Filter message empty on %s with data %s", message.chat.id, filt
                        )
                break

    async def get_filter(self, chat_id: int, keyword: str) -> Optional[str]:
        data = await self.db.find_one(
            {"chat_id": chat_id, f"trigger.{keyword}": {"$exists": True}},
            {f"trigger.{keyword}": 1},
        )
        return data["trigger"][keyword] if data else None

    async def del_filter(self, chat_id: int, keyword: str) -> Tuple[bool, str]:
        filt = self.trigger.get(chat_id)
        if not filt:
            return False, await self.text(chat_id, "filters-chat-nofilter")
        if keyword not in filt:
            return False, await self.text(chat_id, "filters-chat-nokeyword", keyword)

        await self.db.update_one(
            {"chat_id": chat_id},
            {"$unset": {f"trigger.{keyword}": ""}},
        )
        self.trigger[chat_id].remove(keyword)
        return True, ""

    @command.filters(filters.admin_only)
    async def cmd_filter(self, ctx: command.Context) -> str:
        chat = ctx.chat
        if (
            len(ctx.args) < 2
            and not ctx.message.reply_to_message
            or ctx.msg.reply_to_message
            and len(ctx.args) < 1
        ):
            return await self.text(chat.id, "filter-help")

        trigger = ctx.args[0]

        if "." in trigger or "$" in trigger:
            return await self.text(chat.id, "err-illegal-trigger")

        text, types, content, buttons = get_message_info(ctx.msg)
        _, ret = await asyncio.gather(
            self.db.update_one(
                {"chat_id": chat.id},
                {
                    "$set": {
                        f"trigger.{trigger}": {
                            "text": text,
                            "type": types,
                            "content": content,
                            "buttons": buttons,
                        }
                    }
                },
                upsert=True,
            ),
            self.text(chat.id, "filters-added", trigger),
        )

        if self.trigger.get(chat.id):
            self.trigger[chat.id].add(trigger)
        else:
            self.trigger[chat.id] = {trigger}

        return ret

    @command.filters(filters.admin_only)
    async def cmd_stop(self, ctx: command.Context, trigger: str) -> str:
        if not trigger:
            return await self.text(ctx.chat.id, "filter-stop-help")

        deleted, out = await self.del_filter(ctx.chat.id, trigger)
        if not deleted:
            return out

        return await self.text(ctx.chat.id, "filters-removed", trigger)

    @command.filters(filters.admin_only, aliases=["rmallfilters"])
    async def cmd_rmallfilter(self, ctx: command.Context) -> str:
        chat_id = ctx.chat.id
        triggers = self.trigger.pop(chat_id, None)
        if not triggers:
            return await self.text(chat_id, "filters-chat-nofilter")
        await self.db.delete_one({"chat_id": chat_id})
        return await self.text(chat_id, "filters-rmall", len(triggers))

    @command.filters(filters.admin_only)
    async def cmd_filters(self, ctx: command.Context) -> str:
        data = self.trigger.get(ctx.chat.id)
        if not data:
            return await self.text(ctx.chat.id, "filters-chat-nofilter")

        output = await self.text(ctx.chat.id, "filters-list", ctx.chat.title)
        output += "\n".join([f"× `{i}`" for i in sorted(data)])
        return output
