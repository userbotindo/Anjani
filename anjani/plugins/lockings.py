"""Lock/Unlock group Plugin"""
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

import time
import unicodedata as ud
from collections import OrderedDict
from datetime import datetime
from typing import (
    Any,
    Callable,
    ClassVar,
    Coroutine,
    List,
    MutableMapping,
    Optional,
    Set,
    Union,
)

from pyrogram.client import Client
from pyrogram.enums.chat_member_status import ChatMemberStatus
from pyrogram.enums.chat_type import ChatType
from pyrogram.enums.message_entity_type import MessageEntityType
from pyrogram.errors import (
    ChannelPrivate,
    ChatAdminRequired,
    MessageDeleteForbidden,
    MessageIdInvalid,
    PeerIdInvalid,
    UserNotParticipant,
)
from pyrogram.types import ChatPermissions, Message

from anjani import command, filters, plugin, util


async def anon(_: Client, message: Message) -> bool:
    return bool(message.sender_chat)


async def button(_: Client, message: Message) -> bool:
    return bool(message.reply_markup)


async def rtl(_: Client, message: Message) -> bool:
    text = message.text or message.caption
    if not text:
        return False

    checkers = await Lockings.detect_alphabet(text)
    return "arabic" in checkers or "hebrew" in checkers


async def url(_: Client, message: Message) -> bool:
    if not message.entities:
        return False

    for entity in message.entities:
        if entity.type == MessageEntityType.URL:
            return True

    return False


LOCK_TYPES = OrderedDict(
    sorted(
        {
            "audio": filters.audio,
            "animation": filters.animation,
            "document": filters.document,
            "forward": filters.forwarded,
            "photo": filters.photo,
            "sticker": filters.sticker,
            "video": filters.video,
            "contact": filters.contact,
            "location": filters.location,
            "venue": filters.venue,
            "game": filters.game,
            "dice": filters.dice,
            "button": button,
            "inline": filters.via_bot,
            "url": url,
            "bots": "bots",
            "rtl": rtl,
            "anon": anon,
        }.items()
    )
)


class Lockings(plugin.Plugin):
    name: ClassVar[str] = "Lockings"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection
    restrictions: MutableMapping[str, MutableMapping[str, MutableMapping[str, bool]]]

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("LOCKINGS")
        self.restrictions = {
            "lock": self.get_restrictions("lock"),
            "unlock": self.get_restrictions("unlock"),
        }

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        data = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        return {self.name: data} if data else {}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True)

    async def on_message(self, message: Message) -> None:
        if message.outgoing:
            return

        chat = message.chat
        user = message.from_user
        if not chat or chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return

        if not user and message.sender_chat:
            if message.sender_chat.id == chat.id:  # anon admin
                return

            current_chat: Any = await self.bot.get_chat(chat.id)
            if current_chat.linked_chat and message.sender_chat.id == current_chat.linked_chat.id:
                # Linked channel group
                return

        if user:
            try:
                target = await chat.get_member(user.id)
            except (ChatAdminRequired, ChannelPrivate, PeerIdInvalid, UserNotParticipant):
                pass
            else:
                if target.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                    return

        locked = await self.get_chat_restrictions(chat.id)
        for lock_type in locked:
            try:
                func: Union[
                    str, Callable[[Client, Message], Coroutine[Any, Any, bool]]
                ] = LOCK_TYPES[lock_type]
                if not callable(func):
                    continue

                if await func(self.bot.client, message):
                    await message.delete()
            except MessageDeleteForbidden:
                await self.bot.respond(
                    message,
                    await self.get_text(chat.id, "lockings-failed-to-delete", lock_type=lock_type),
                    quote=True,
                )
            except MessageIdInvalid:
                continue
            except Exception as e:  # skipcq: PYL-W0703
                self.log.error(e, exc_info=e)
                continue

    async def on_chat_action(self, action: Message) -> None:
        chat = action.chat
        added_by = action.from_user
        if action.left_chat_member:
            return

        locked = await self.get_chat_restrictions(chat.id)
        if not locked or locked and "bots" not in locked:
            return

        bot_perm, added_by_perm = await util.tg.fetch_permissions(
            self.bot.client, chat.id, added_by.id
        )
        if not (bot_perm and added_by_perm) or added_by_perm.status == ChatMemberStatus.OWNER:
            return  # bot added by owner

        # Kick the bot if it's not added by the owner
        for member in action.new_chat_members:
            if not member.is_bot:
                continue

            if bot_perm.status != ChatMemberStatus.ADMINISTRATOR:
                await self.bot.respond(
                    action, await self.get_text(chat.id, "lockings-bots-not-admin"), quote=True
                )
                return  # Tell once so we don't spam the chat

            try:
                await chat.ban_member(
                    member.id, until_date=datetime.fromtimestamp(int(time.time() + 30))
                )
            except UserNotParticipant:  # Bot probably kicked already
                continue

    @staticmethod
    async def detect_alphabet(ustring: str) -> Set[str]:
        return {ud.name(char).split(" ")[0].lower() for char in ustring if char.isalpha()}

    @staticmethod
    def get_mode(mode: str) -> bool:
        return mode != "lock"

    def get_restrictions(self, mode: str) -> MutableMapping[str, MutableMapping[str, bool]]:
        return OrderedDict(
            sorted(
                {
                    "all": {
                        "can_send_messages": self.get_mode(mode),
                        "can_send_media_messages": self.get_mode(mode),
                        "can_send_polls": self.get_mode(mode),
                        "can_send_other_messages": self.get_mode(mode),
                        "can_add_web_page_previews": self.get_mode(mode),
                        "can_change_info": self.get_mode(mode),
                        "can_invite_users": self.get_mode(mode),
                        "can_pin_messages": self.get_mode(mode),
                    },
                    "messages": {"can_send_messages": self.get_mode(mode)},
                    "media": {"can_send_media_messages": self.get_mode(mode)},
                    "polls": {"can_send_polls": self.get_mode(mode)},
                    "other": {"can_send_other_messages": self.get_mode(mode)},
                    "previews": {"can_add_web_page_previews": self.get_mode(mode)},
                    "info": {"can_change_info": self.get_mode(mode)},
                    "invite": {"can_invite_users": self.get_mode(mode)},
                    "pin": {"can_pin_messages": self.get_mode(mode)},
                }.items()
            )
        )

    async def get_chat_restrictions(self, chat_id: int) -> List[str]:
        data = await self.db.find_one({"chat_id": chat_id}, {"type": 1})
        return data["type"] if data else []

    def unpack_permissions(
        self, permissions: MutableMapping[str, bool], mode: str, lock_type: str
    ) -> ChatPermissions:
        try:
            del permissions["_client"]
        except KeyError:
            pass

        permissions.update(self.restrictions[mode][lock_type])
        return ChatPermissions(**permissions)

    async def update_chat_restrictions(self, chat_id: int, types: str, mode: str) -> None:
        if mode == "lock":
            aggregation = "$push"
        elif mode == "unlock":
            aggregation = "$pull"
        else:
            raise ValueError("Invalid mode")

        await self.db.update_one({"chat_id": chat_id}, {aggregation: {"type": types}}, upsert=True)

    @command.filters(filters.admin_only, aliases={"listlocks", "locks", "locked", "locklist"})
    async def cmd_list_locks(self, ctx: command.Context) -> str:
        chat = ctx.chat
        permissions = dict(chat.permissions.__dict__)
        try:
            del permissions["_client"]
        except KeyError:
            pass

        text = await ctx.get_text("lockings-types-perm")
        for types, is_lock in permissions.items():
            if not is_lock:
                text += f"\n × `{types}`"

        locked = await self.get_chat_restrictions(chat.id)
        if not locked and all(value is True for value in permissions.values()):
            return await ctx.get_text("lockings-types-list-empty")

        text += "\n\n" + await ctx.get_text("lockings-types-list")
        for types in sorted(locked):
            text += f"\n × `{types}`"

        return text

    @command.filters(filters.admin_only)
    async def cmd_lock(self, ctx: command.Context, lock_type: Optional[str] = None) -> str:
        chat = ctx.chat
        if not lock_type:
            return await ctx.get_text("lockings-type-required")

        lock_type = lock_type.lower()
        permissions = dict(chat.permissions.__dict__)
        if lock_type in self.restrictions["lock"]:
            if (
                not permissions[list(self.restrictions["lock"][lock_type].keys())[0]]
                and lock_type != "all"
            ):
                return await ctx.get_text("lockings-type-locked", lock_type=lock_type)

            await self.bot.client.set_chat_permissions(
                chat_id=chat.id,
                permissions=self.unpack_permissions(permissions, "lock", lock_type),
            )
        elif lock_type in LOCK_TYPES:
            locked = await self.get_chat_restrictions(chat.id)
            if lock_type in locked:
                return await ctx.get_text("lockings-type-locked", lock_type=lock_type)

            await self.update_chat_restrictions(chat.id, lock_type, "lock")
        else:
            return await ctx.get_text("lockings-type-invalid", lock_type=lock_type)

        return await ctx.get_text("lockings-type-done", lock_type=lock_type)

    @command.filters(filters.admin_only, aliases={"locktypes"})
    async def cmd_lock_types(self, ctx: command.Context) -> str:
        text = ""
        for types in sorted(list(LOCK_TYPES) + list(self.restrictions["lock"])):
            text += f"\n × `{types}`"

        return (
            await ctx.get_text("lockings-types-available") + text + await ctx.get_text("types-note")
        )

    @command.filters(filters.admin_only)
    async def cmd_unlock(self, ctx: command.Context, unlock_type: Optional[str] = None) -> str:
        chat = ctx.chat
        if not unlock_type:
            return await ctx.get_text("unlockings-type-required")

        unlock_type = unlock_type.lower()
        permissions = dict(chat.permissions.__dict__)
        if unlock_type in self.restrictions["unlock"]:
            if (
                permissions[list(self.restrictions["unlock"][unlock_type].keys())[0]]
                and unlock_type != "all"
            ):
                return await ctx.get_text("unlockings-type-unlocked", unlock_type=unlock_type)

            await self.bot.client.set_chat_permissions(
                chat_id=chat.id,
                permissions=self.unpack_permissions(permissions, "unlock", unlock_type),
            )
        elif unlock_type in LOCK_TYPES:
            locked = await self.get_chat_restrictions(chat.id)
            if not locked or unlock_type not in locked:
                return await ctx.get_text("unlockings-type-unlocked", unlock_type=unlock_type)

            await self.update_chat_restrictions(chat.id, unlock_type, "unlock")
        else:
            return await ctx.get_text("unlockings-type-invalid", unlock_type=unlock_type)

        return await ctx.get_text("unlockings-type-done", unlock_type=unlock_type)
