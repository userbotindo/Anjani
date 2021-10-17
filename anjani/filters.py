from typing import Any, Callable, Coroutine, Optional

from pyrogram import Client
from pyrogram.filters import (
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
    edited,
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
    web_page,
    venue,
    via_bot,
    video,
    video_note,
    voice,
    voice_chat_ended,
    voice_chat_members_invited,
    voice_chat_started,
)
from pyrogram.types import Message

from anjani.util.tg import fetch_permissions, is_staff_or_admin
from anjani.util.types import CustomFilter

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
    "edited",
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
    "voice",
    "voice_chat_ended",
    "voice_chat_members_invited",
    "voice_chat_started"
]


def create(func: FilterFunc, name: str = None, **kwargs: Any) -> CustomFilter:
    return type(
        name or func.__name__ or "CustomAnjaniFilter", (CustomFilter,), {"__call__": func, **kwargs}
    )()


# { permission
def _create_filter_permission(name: str) -> Filter:
    async def func(flt: CustomFilter, client: Client, message: Message) -> bool:
        if message.chat.type == "private":
            return False

        bot_perm, member_perm = await fetch_permissions(
            client, message.chat.id, message.from_user.id
        )
        try:
            return getattr(bot_perm, name) and getattr(member_perm, name)
        except AttributeError:
            flt.anjani.log.error(f"{name} is not a valid permission")
            return False

    return create(func, name, include_bot=True)


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
        if rank is None:
            return target.id in flt.anjani.staff
        if rank == "dev":
            return target.id in flt.anjani.devs
        return False

    return create(func, "staff_only", include_bot=include_bot)


staff_only = _staff_only()
dev_only = _staff_only(rank="dev")
# }


# { owner_only
def _owner_only(include_bot: bool = True) -> CustomFilter:
    async def func(flt: CustomFilter, _: Client, message: Message) -> bool:
        target = message.from_user
        return target.id == flt.anjani.owner

    return create(func, "owner_only", include_bot=include_bot)


owner_only = _owner_only()
# }


# { admin_only
def _admin_only(include_bot: bool = True) -> CustomFilter:
    async def func(flt: CustomFilter, client: Client, message: Message) -> bool:  # skipcq: PYL-W0613
        if message.chat.type == "private":
            return False

        target = message.from_user
        bot_perm, member_perm = await fetch_permissions(client, message.chat.id, target.id)
        return bot_perm.status == "administrator" and is_staff_or_admin(member_perm)

    return create(func, "admin_only", include_bot=include_bot)


admin_only = _admin_only()
# }
