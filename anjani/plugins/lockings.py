"""Lock/Unlock group Plugin"""
# Copyright (C) 2020 - 2022  UserbotIndo Team, <https://github.com/userbotindo.git>
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
from typing import ClassVar, List, MutableMapping, Optional, Set

from pyrogram.enums.chat_member_status import ChatMemberStatus
from pyrogram.enums.message_entity_type import MessageEntityType
from pyrogram.errors import MessageDeleteForbidden, MessageIdInvalid, UserNotParticipant
from pyrogram.types import ChatPermissions, Message

from anjani import command, filters, listener, plugin, util

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
            "poll": filters.poll,
            "dice": filters.dice,
            "button": "button",
            "inline": filters.via_bot,
            "url": "url",
            "bots": "bots",
            "rtl": "rtl",
        }.items()
    )
)


class Lockings(plugin.Plugin):
    name: ClassVar[str] = "Lockings"
    helpable: ClassVar[bool] = False  # TODO: implement helpable

    db: util.db.AsyncCollection
    restrictions: MutableMapping[str, MutableMapping[str, MutableMapping[str, bool]]]

    async def detect_alphabet(self, ustring: str) -> Set[str]:
        return set(ud.name(char).split(" ")[0].lower() for char in ustring if char.isalpha())

    def get_mode(self, mode: str) -> bool:
        return False if mode == "lock" else True

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
                    "sticker": {"can_send_other_messages": self.get_mode(mode)},
                    "gif": {"can_send_other_messages": self.get_mode(mode)},
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
        data = await self.db.find_one({"_id": chat_id})
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

        await self.db.update_one({"_id": chat_id}, {aggregation: {"type": types}}, upsert=True)

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("LOCKINGS")
        self.restrictions = {
            "lock": self.get_restrictions("lock"),
            "unlock": self.get_restrictions("unlock"),
        }

    @listener.filters(~filters.admin_only_no_report & filters.group)
    async def on_message(self, message: Message) -> None:
        chat = message.chat
        locked = await self.get_chat_restrictions(chat.id)
        for lock_type in locked:
            try:
                if lock_type == "bots":
                    continue

                if lock_type == "button" and message.reply_markup:
                    await message.delete()
                    continue

                text = message.text or message.caption
                if lock_type == "rtl" and text:
                    checkers = await self.detect_alphabet(text)
                    if "arabic" in checkers:
                        await message.delete()

                    continue

                if lock_type == "url" and message.entities:
                    for entity in message.entities:
                        if entity.type == MessageEntityType.URL:
                            await message.delete()
                            break

                    continue

                is_locked: bool = await LOCK_TYPES[lock_type](self.bot.client, message)
                if is_locked:
                    await message.delete()
            except MessageDeleteForbidden:
                await self.bot.respond(
                    message,
                    await self.get_text(chat.id, "locking-failed-to-delete", lock_type=lock_type),
                    quote=True,
                )
            except MessageIdInvalid:  # Probably deleted already
                continue
            except Exception as e:
                self.log.error(e)
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
        if added_by_perm.status == ChatMemberStatus.OWNER:
            return  # bot added by owner

        # Kick the bot if it's not added by the owner
        for member in action.new_chat_members:
            if not member.is_bot:
                continue

            if bot_perm.status != ChatMemberStatus.ADMINISTRATOR:
                await self.bot.respond(
                    action, await self.get_text(chat.id, "locking-bots-not-admin"), quote=True
                )
                return  # Tell once so we don't spam the chat

            try:
                await chat.ban_member(
                    member.id, until_date=datetime.fromtimestamp(int(time.time() + 30))
                )
            except UserNotParticipant:  # Bot probably kicked already
                continue

    @command.filters(filters.admin_only, aliases={"listlocks", "locks", "locked", "locklist"})
    async def cmd_list_locks(self, ctx: command.Context) -> str:
        chat = ctx.chat
        locked = await self.get_chat_restrictions(chat.id)
        if not locked:
            return await ctx.get_text("lock-types-list-empty")

        text = ""
        for types in sorted(locked):
            text += f"\n × `{types}`"

        return await ctx.get_text("lock-types-list") + text

    @command.filters(filters.admin_only)
    async def cmd_lock(self, ctx: command.Context, lock_type: Optional[str] = None) -> str:
        chat = ctx.chat
        if not lock_type:
            return await ctx.get_text("lock-type-required")

        lock_type = lock_type.lower()
        permissions = dict(chat.permissions.__dict__)
        if lock_type in self.restrictions["lock"]:
            if (
                not permissions[list(self.restrictions["lock"][lock_type].keys())[0]]
                and lock_type != "all"
            ):
                return await ctx.get_text("lock-type-locked", lock_type=lock_type)

            await self.bot.client.set_chat_permissions(
                chat_id=chat.id,
                permissions=self.unpack_permissions(permissions, "lock", lock_type),
            )
        elif lock_type in LOCK_TYPES:
            locked = await self.get_chat_restrictions(chat.id)
            if lock_type in locked:
                return await ctx.get_text("lock-type-locked", lock_type=lock_type)

            await self.update_chat_restrictions(chat.id, lock_type, "lock")
        else:
            return await ctx.get_text("lock-type-invalid", lock_type=lock_type)

        return await ctx.get_text("lock-type-done", lock_type=lock_type)

    @command.filters(filters.admin_only, aliases={"locktypes"})
    async def cmd_lock_types(self, ctx: command.Context) -> str:
        text = ""
        for types in list(LOCK_TYPES) + list(self.restrictions["lock"]):
            text += f"\n × `{types}`"

        return await ctx.get_text("lock-types-available") + text

    @command.filters(filters.admin_only)
    async def cmd_unlock(self, ctx: command.Context, unlock_type: Optional[str] = None) -> str:
        chat = ctx.chat
        if not unlock_type:
            return await ctx.get_text("unlock-type-required")

        unlock_type = unlock_type.lower()
        permissions = dict(chat.permissions.__dict__)
        if unlock_type in self.restrictions["unlock"]:
            if (
                permissions[list(self.restrictions["unlock"][unlock_type].keys())[0]]
                and unlock_type != "all"
            ):
                return await ctx.get_text("unlock-type-unlocked", unlock_type=unlock_type)

            await self.bot.client.set_chat_permissions(
                chat_id=chat.id,
                permissions=self.unpack_permissions(permissions, "unlock", unlock_type),
            )
        elif unlock_type in LOCK_TYPES:
            locked = await self.get_chat_restrictions(chat.id)
            if not locked or unlock_type not in locked:
                return await ctx.get_text("unlock-type-unlocked", unlock_type=unlock_type)

            await self.update_chat_restrictions(chat.id, unlock_type, "unlock")
        else:
            return await ctx.get_text("unlock-type-invalid", unlock_type=unlock_type)

        return await ctx.get_text("unlock-type-done", unlock_type=unlock_type)
