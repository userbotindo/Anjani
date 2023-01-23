"""Anjani filters"""
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

from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional

from pyrogram.client import Client
from pyrogram.enums.chat_member_status import ChatMemberStatus
from pyrogram.enums.chat_type import ChatType
from pyrogram.filters import (  # skipcq: PY-W2000
    Filter,
    animation,
    audio,
    bot,
    caption,
    channel,
    channel_chat_created,
    chat,
    command,
    contact,
    delete_chat_photo,
    dice,
    document,
    forwarded,
    from_scheduled,
    game,
    game_high_score,
    group,
    group_chat_created,
    incoming,
    inline_keyboard,
    left_chat_member,
    linked_channel,
    location,
    me,
    media,
    media_group,
    mentioned,
    migrate_from_chat_id,
    migrate_to_chat_id,
    new_chat_members,
    new_chat_photo,
    new_chat_title,
    outgoing,
    photo,
    pinned_message,
    poll,
    private,
    regex,
    reply,
    reply_keyboard,
    scheduled,
    service,
    sticker,
    supergroup_chat_created,
    text,
    user,
    venue,
    via_bot,
    video,
    video_chat_ended,
    video_chat_members_invited,
    video_chat_started,
    video_note,
    web_page,
)
from pyrogram.types import ChatMember, Message

from anjani.util.tg import fetch_permissions, get_text, reply_and_delete
from anjani.util.types import CustomFilter

if TYPE_CHECKING:
    from anjani.core import Anjani


FilterFunc = Callable[[CustomFilter, Client, Message], Coroutine[Any, Any, bool]]
__all__ = [
    "admin_only",
    "animation",
    "audio",
    "bot",
    "can_change_info",
    "can_delete",
    "can_invite",
    "can_pin",
    "can_promote",
    "can_restrict",
    "caption",
    "channel",
    "channel_chat_created",
    "chat",
    "command",
    "contact",
    "delete_chat_photo",
    "dev_only",
    "dice",
    "document",
    "forwarded",
    "from_scheduled",
    "game",
    "game_high_score",
    "group",
    "group_chat_created",
    "incoming",
    "inline_keyboard",
    "left_chat_member",
    "linked_channel",
    "location",
    "me",
    "media",
    "media_group",
    "mentioned",
    "migrate_from_chat_id",
    "migrate_to_chat_id",
    "new_chat_members",
    "new_chat_photo",
    "new_chat_title",
    "outgoing",
    "owner_only",
    "photo",
    "pinned_message",
    "poll",
    "private",
    "regex",
    "reply",
    "reply_keyboard",
    "scheduled",
    "service",
    "staff_only",
    "sticker",
    "supergroup_chat_created",
    "text",
    "user",
    "web_page",
    "venue",
    "via_bot",
    "video",
    "video_note",
    "video",
    "video_chat_ended",
    "video_chat_members_invited",
    "video_chat_started",
]


def create(func: FilterFunc, name: Optional[str] = None, **kwargs: Any) -> CustomFilter:
    return type(
        name or func.__name__ or "CustomAnjaniFilter", (CustomFilter,), {"__call__": func, **kwargs}
    )()


# { permission
def _create_filter_permission(name: str, *, include_bot: bool = True) -> Filter:
    async def func(flt: CustomFilter, client: Client, message: Message) -> bool:
        target, priv = message.from_user, message.chat and message.chat.type == ChatType.PRIVATE
        if priv or not target or not message.chat:
            return False

        bot_perm, member_perm = await fetch_permissions(client, message.chat.id, target.id)
        if not (bot_perm and member_perm) or not (bot_perm.privileges and member_perm.privileges):
            return False

        try:
            if getattr(bot_perm.privileges, name) and getattr(member_perm.privileges, name):
                return True
        except AttributeError:
            flt.anjani.log.error(f"{name} is not a valid permission")
            return False

        flt.anjani.loop.create_task(
            reply_and_delete(
                message, await get_text(flt.anjani, message.chat.id, "err-perm", name), 5
            )
        )
        return False

    return create(func, name, include_bot=include_bot)


can_change_info = _create_filter_permission("can_change_info")
can_delete = _create_filter_permission("can_delete_messages")
can_invite = _create_filter_permission("can_invite_users")
can_pin = _create_filter_permission("can_pin_messages")
can_promote = _create_filter_permission("can_promote_members")
can_restrict = _create_filter_permission("can_restrict_members")
# }


# { staff_only
def _staff_only(include_bot: bool = True, *, rank: Optional[str] = None) -> CustomFilter:
    async def func(flt: CustomFilter, _: Client, message: Message) -> bool:
        target = message.from_user
        if not target:  # Sanity check for anonymous admin
            return False

        if rank is None:
            return target.id in flt.anjani.staff

        if rank == "dev":
            return target.id in flt.anjani.devs

        flt.anjani.log.error(f"Invalid rank: {rank}")
        return False

    return create(func, "staff_only", include_bot=include_bot)


staff_only = _staff_only()
dev_only = _staff_only(rank="dev")
# }


# { owner_only
def _owner_only(include_bot: bool = True) -> CustomFilter:
    async def func(flt: CustomFilter, _: Client, message: Message) -> bool:
        target = message.from_user
        if not target:  # Sanity check for anonymous admin
            return False

        return target.id == flt.anjani.owner

    return create(func, "owner_only", include_bot=include_bot)


owner_only = _owner_only()
# }


# { admin_only
async def _send_error(robot: "Anjani", chat_id: int, message: Message, string_key: str) -> None:
    robot.loop.create_task(reply_and_delete(message, await get_text(robot, chat_id, string_key), 5))


def is_admin(target: ChatMember) -> bool:
    return target.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}


def _admin_only(include_bot: bool = True, send_error: bool = True) -> CustomFilter:
    async def func(flt: CustomFilter, client: Client, message: Message) -> bool:
        target, priv = message.from_user, message.chat and message.chat.type == ChatType.PRIVATE
        if priv or not message.chat:
            return False

        if not target:
            if message.sender_chat:
                if message.sender_chat.id == message.chat.id:  # Anonymous Admin
                    return True

                curr_chat: Any = await client.get_chat(message.chat.id)
                if (
                    curr_chat.linked_chat
                    and message.sender_chat.id == curr_chat.linked_chat.id
                    and not message.forward_from_chat
                ):  # Linked Channel Owner
                    return True

            return False

        bot_perm, member_perm = await fetch_permissions(client, message.chat.id, target.id)
        if not bot_perm:
            if send_error:
                await _send_error(flt.anjani, message.chat.id, message, "err-im-not-admin")

            return False

        if not member_perm:
            if send_error:
                await _send_error(flt.anjani, message.chat.id, message, "err-not-admin")

            return False

        user_admin = is_admin(member_perm)
        bot_admin = is_admin(bot_perm)
        if bot_admin and user_admin:
            return True

        if send_error:
            if not bot_admin and user_admin:
                # Bot is not admin, but user is
                await _send_error(flt.anjani, message.chat.id, message, "err-im-not-admin")
            elif bot_admin and not user_admin:
                # Bot is admin, but user is not
                await _send_error(flt.anjani, message.chat.id, message, "err-not-admin")
            else:
                await _send_error(flt.anjani, message.chat.id, message, "err-perm")

        return False

    return create(func, "admin_only", include_bot=include_bot)


admin_only = _admin_only()
admin_only_no_report = _admin_only(send_error=False)
"""Set filter to admin only but without sending error message"""
# }
