"""Anjani telegram utils"""
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
import html
import re
from typing import TYPE_CHECKING, AsyncGenerator, List, Optional, Tuple, Union

from pyrogram.client import Client
from pyrogram.enums.chat_member_status import ChatMemberStatus
from pyrogram.enums.chat_members_filter import ChatMembersFilter
from pyrogram.errors import (
    ChannelPrivate,
    ChatForbidden,
    ChatWriteForbidden,
    MessageDeleteForbidden,
    UserNotParticipant,
)
from pyrogram.filters import AndFilter, Filter, InvertFilter, OrFilter
from pyrogram.types import (
    ChatMember,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)

from ..constant import MESSAGE_CHAR_LIMIT, STAFF, TRUNCATION_SUFFIX
from ..types import Button, CustomFilter
from .enum import MessageType

if TYPE_CHECKING:
    from anjani.core import Anjani


def build_button(buttons: Button) -> InlineKeyboardMarkup:
    """Build saved button format"""
    keyb = []  # type: List[List[InlineKeyboardButton]]
    for btn in buttons:
        if btn[2] and keyb:
            keyb[-1].append(InlineKeyboardButton(btn[0], url=btn[1]))
        else:
            keyb.append([InlineKeyboardButton(btn[0], url=btn[1])])
    return InlineKeyboardMarkup(keyb)


def revert_button(button: Button) -> str:
    """Revert button format"""
    res = ""
    for btn in button:
        if btn[2]:
            res += f"\n[{btn[0]}](buttonurl://{btn[1]}:same)"
        else:
            res += f"\n[{btn[0]}](buttonurl://{btn[1]})"
    return res


def parse_button(text: str) -> Tuple[str, Button]:
    """Parse button to save"""
    regex = re.compile(r"(\[([^\[]+?)\]\(buttonurl:(?:/{0,2})(.+?)(:same)?\))")

    prev = 0
    parser_data = ""
    buttons = []  # type: List[Tuple[str, str, bool]]
    for match in regex.finditer(text):
        # escape check
        md_escaped = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            md_escaped += 1
            to_check -= 1

        # if != "escaped" -> Create button: btn
        if md_escaped % 2 == 0:
            # create a thruple with button label, url, and newline status
            buttons.append((match.group(2), match.group(3), bool(match.group(4))))
            parser_data += text[prev : match.start(1)]
            prev = match.end(1)
        # if odd, escaped -> move along
        else:
            parser_data += text[prev:to_check]
            prev = match.start(1) - 1

    parser_data += text[prev:]

    return parser_data.rstrip(), buttons


def get_message_info(msg: Message) -> Tuple[str, MessageType, Optional[str], Button]:
    """Parse received message and return its content."""
    types = None
    content = None
    text = ""
    buttons = []

    reply_msg = msg.reply_to_message

    if reply_msg:
        text = reply_msg.text or reply_msg.caption
        added_text = None
        if text:
            text, buttons = parse_button(text.markdown)
        else:
            # added_text are from user input
            added_text, buttons = parse_button(msg.text.markdown.split(" ", 2)[-1])

        if not text and added_text is not None:
            text = added_text

        if reply_msg.text:
            types = MessageType.BUTTON_TEXT if buttons else MessageType.TEXT
        elif reply_msg.sticker:
            content, types = reply_msg.sticker.file_id, MessageType.STICKER
        elif reply_msg.document:
            content, types = reply_msg.document.file_id, MessageType.DOCUMENT
        elif reply_msg.photo:
            content, types = reply_msg.photo.file_id, MessageType.PHOTO
        elif reply_msg.audio:
            content, types = reply_msg.audio.file_id, MessageType.AUDIO
        elif reply_msg.voice:
            content, types = reply_msg.voice.file_id, MessageType.VOICE
        elif reply_msg.video:
            content, types = reply_msg.video.file_id, MessageType.VIDEO
        elif reply_msg.video_note:
            content, types = reply_msg.video_note.file_id, MessageType.VIDEO_NOTE
        elif reply_msg.animation:
            content, types = reply_msg.animation.file_id, MessageType.ANIMATION
        else:
            raise ValueError("Can't get message information")
    else:
        text, buttons = parse_button(msg.text.markdown.split(" ", 2)[2])
        types = MessageType.BUTTON_TEXT if buttons else MessageType.TEXT

    return text, types, content, buttons


def truncate(text: str) -> str:
    """Truncates the given text to fit in one Telegram message."""

    if len(text) > MESSAGE_CHAR_LIMIT:
        return text[: MESSAGE_CHAR_LIMIT - len(TRUNCATION_SUFFIX)] + TRUNCATION_SUFFIX

    return text


def is_staff_or_admin(target: ChatMember) -> bool:
    return (
        target.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}
        or target.user.id in STAFF
    )


def is_staff(target_id: int) -> bool:
    return target_id in STAFF


def mention(user: User) -> str:
    pattern = re.compile(r"<[a-z/][\s\S]*>")
    link = "[{name}](tg://user?id={id})"
    return (
        link.format(name=html.escape(user.first_name), id=user.id)
        if pattern.search(user.first_name)
        else link.format(name=user.first_name, id=user.id)
    )


# { Permission
# Aliases
Bot = ChatMember
Member = ChatMember


async def fetch_permissions(
    client: Client, chat: int, user: int
) -> Tuple[Optional[Bot], Optional[Member]]:
    try:
        bot, member = await asyncio.gather(
            client.get_chat_member(chat, "me"), client.get_chat_member(chat, user)
        )
        return bot, member
    except UserNotParticipant:
        return None, None


# }


# { ChatAdmin
async def get_chat_admins(
    client: Client, chat: int, *, exclude_bot: bool = False
) -> AsyncGenerator[ChatMember, None]:
    member: ChatMember
    async for member in client.get_chat_members(chat, filter=ChatMembersFilter.ADMINISTRATORS):  # type: ignore
        if member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
            if exclude_bot and member.user.is_bot:
                continue
            yield member


# }


# { Non-Context reply then delete
async def reply_and_delete(message: Message, text: str, del_in: int = 1) -> None:
    if del_in < 1:
        raise ValueError("Delay must be greater than 0")

    try:
        to_del, _ = await asyncio.gather(
            message.reply(text, quote=True),
            asyncio.sleep(del_in),
        )
    except (ChatForbidden, ChannelPrivate, ChatWriteForbidden):
        return

    try:
        await asyncio.gather(message.delete(), to_del.delete())
    except MessageDeleteForbidden:
        pass

    return


def check_filters(filters: Union[Filter, CustomFilter], anjani: "Anjani") -> None:
    """Recursively check filters to set :obj:`~Anjani` into :obj:`~CustomFilter` if needed"""
    if isinstance(filters, (AndFilter, OrFilter, InvertFilter)):
        check_filters(filters.base, anjani)
    if isinstance(filters, (AndFilter, OrFilter)):
        check_filters(filters.other, anjani)

    # Only accepts CustomFilter instance
    if getattr(filters, "include_bot", False) and isinstance(filters, CustomFilter):
        filters.anjani = anjani


# }
