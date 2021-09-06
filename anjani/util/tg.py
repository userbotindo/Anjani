import asyncio
import re
from enum import IntEnum, unique
from typing import AsyncGenerator, List, Optional, Set, Tuple, Union

from pyrogram import Client
from pyrogram.types import (
    ChatMember,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message
)

Button = Union[
    Tuple[Tuple[str, str, bool]],
    List[Tuple[str, str, bool]]
]

MESSAGE_CHAR_LIMIT = 4096
TRUNCATION_SUFFIX = "... (truncated)"


@unique
class Types(IntEnum):
    """A Class representing message type"""
    TEXT = 0
    BUTTON_TEXT = 1
    DOCUMENT = 2
    PHOTO = 3
    VIDEO = 4
    STICKER = 5
    AUDIO = 6
    VOICE = 7
    VIDEO_NOTE = 8
    ANIMATION = 9


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
    # Remove any markdown button left over if any
    t = parser_data.rstrip().split()
    if t:
        pattern = re.compile(r"[_-`*~]+")
        anyMarkdownLeft = pattern.search(t[-1])
        if anyMarkdownLeft:
            toRemove = anyMarkdownLeft[0][0]
            t[-1] = t[-1].replace(toRemove, "")
            return " ".join(t), buttons

    return parser_data.rstrip(), buttons


def get_message_info(msg: Message) -> Tuple[str, Types, Optional[str], Button]:
    """Parse recieved message and return all its content"""
    types = None
    content = None
    text = ""
    buttons = []  # type: Button

    if msg.reply_to_message:
        t = msg.reply_to_message.text or msg.reply_to_message.caption
        if t:
            text, buttons = parse_button(t.markdown)

        if msg.reply_to_message.text:
            types = Types.BUTTON_TEXT if buttons else Types.TEXT
        elif msg.reply_to_message.sticker:
            content = msg.reply_to_message.sticker.file_id
            types = Types.STICKER
        elif msg.reply_to_message.document:
            content = msg.reply_to_message.document.file_id
            types = Types.DOCUMENT
        elif msg.reply_to_message.photo:
            content = msg.reply_to_message.photo.file_id
            types = Types.PHOTO
        elif msg.reply_to_message.audio:
            content = msg.reply_to_message.audio.file_id
            types = Types.AUDIO
        elif msg.reply_to_message.voice:
            content = msg.reply_to_message.voice.file_id
            types = Types.VOICE
        elif msg.reply_to_message.video:
            content = msg.reply_to_message.video.file_id
            types = Types.VIDEO
        elif msg.reply_to_message.video_note:
            content = msg.reply_to_message.video_note.file_id
            types = Types.VIDEO_NOTE
        elif msg.reply_to_message.animation:
            content = msg.reply_to_message.animation.file_id
            types = Types.ANIMATION
        else:
            raise ValueError("Can't get message information")
    else:
        args = msg.text.markdown.split(" ", 2)
        text, buttons = parse_button(args[2])
        types = Types.BUTTON_TEXT if buttons else Types.TEXT

    return text, types, content, buttons


def truncate(text: str) -> str:
    """Truncates the given text to fit in one Telegram message."""

    if len(text) > MESSAGE_CHAR_LIMIT:
        return text[: MESSAGE_CHAR_LIMIT - len(TRUNCATION_SUFFIX)] + TRUNCATION_SUFFIX

    return text


def is_staff_or_admin(target: ChatMember, staff: Set[int]) -> bool:
    return (
        target.status in {"administrator", "creator"} or
        target.user.id in staff
    )


# { Permission
async def fetch_permissions(
    client: Client, chat: int, user: int
) -> Tuple[ChatMember, ChatMember]:
    bot, member = await asyncio.gather(client.get_chat_member(chat, "me"),
                                       client.get_chat_member(chat, user))
    return bot, member
# }


# { ChatAdmin
async def get_chat_admins(client: Client, chat: int) -> AsyncGenerator[ChatMember, None]:
    member: ChatMember
    async for member in client.iter_chat_members(chat, filter="administrators"):  # type: ignore
        if member.status in {"administrator", "creator"}:
            yield member
# }