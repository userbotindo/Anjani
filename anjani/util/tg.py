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
import codecs
import html
import re
from enum import IntEnum, unique
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

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
from pyrogram.types import (
    ChatMember,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    User,
)
from typing_extensions import ParamSpecArgs, ParamSpecKwargs

from anjani.util import types as _types
from anjani.util.async_helper import run_sync

if TYPE_CHECKING:
    from anjani.core import Anjani

MESSAGE_CHAR_LIMIT = 4096
STAFF: Set[int] = set()
TRUNCATION_SUFFIX = "... (truncated)"

Button = Union[Tuple[Tuple[str, str, bool]], List[Tuple[str, str, bool]]]


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
    # t = parser_data.rstrip().split()
    # if t:
    #     pattern = re.compile(r"[_-`*~]+")
    #     anyMarkdownLeft = pattern.search(t[-1])
    #     if anyMarkdownLeft:
    #         toRemove = anyMarkdownLeft[0][0]
    #         t[-1] = t[-1].replace(toRemove, "")
    #         return " ".join(t), buttons

    return parser_data.rstrip(), buttons


def get_message_info(msg: Message) -> Tuple[str, Types, Optional[str], Button]:
    """Parse received message and return its content."""
    types = None
    content = None
    text = ""
    buttons = []

    reply_msg = msg.reply_to_message

    if reply_msg:
        text = reply_msg.text or reply_msg.caption
        if text:
            text, buttons = parse_button(text.markdown)

        if reply_msg.text:
            types = Types.BUTTON_TEXT if buttons else Types.TEXT
        elif reply_msg.sticker:
            content, types = reply_msg.sticker.file_id, Types.STICKER
        elif reply_msg.document:
            content, types = reply_msg.document.file_id, Types.DOCUMENT
        elif reply_msg.photo:
            content, types = reply_msg.photo.file_id, Types.PHOTO
        elif reply_msg.audio:
            content, types = reply_msg.audio.file_id, Types.AUDIO
        elif reply_msg.voice:
            content, types = reply_msg.voice.file_id, Types.VOICE
        elif reply_msg.video:
            content, types = reply_msg.video.file_id, Types.VIDEO
        elif reply_msg.video_note:
            content, types = reply_msg.video_note.file_id, Types.VIDEO_NOTE
        elif reply_msg.animation:
            content, types = reply_msg.animation.file_id, Types.ANIMATION
        else:
            raise ValueError("Can't get message information")
    else:
        text, buttons = parse_button(msg.text.markdown.split(" ", 2)[2])
        types = Types.BUTTON_TEXT if buttons else Types.TEXT

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


# }


# { GetText Language
def __loop_safe(
    func: Callable[
        [
            _types.Bot,
            _types.ChatId,
            _types.TextName,
            ParamSpecArgs,
            _types.NoFormat,
            ParamSpecKwargs,
        ],
        str,
    ]
):  # Special: let default typing choose the return type
    """Decorator for get_text functions"""

    @wraps(func)
    async def wrapper(
        bot: "Anjani",
        chat_id: Optional[int],
        text_name: str,
        *args: Any,
        noformat: bool = False,
        **kwargs: Any,
    ) -> str:
        """Parse the string with user language setting.

        Parameters:
            bot (`Anjani`):
                The bot instance.
            chat_id (`int`, *Optional*):
                Id of the sender(PM's) or chat_id to fetch the user language setting.
                If chat_id is None, the language will always use 'en'.
            text_name (`str`):
                String name to parse. The string is parsed from YAML documents.
            *args (`any`, *Optional*):
                One or more values that should be formatted and inserted in the string.
                The value should be in order based on the language string placeholder.
            noformat (`bool`, *Optional*):
                If True, the text returned will not be formated.
                Default to False.
            **kwargs (`any`, *Optional*):
                One or more keyword values that should be formatted and inserted in the string.
                based on the keyword on the language strings.
        """
        return await run_sync(func, bot, chat_id, text_name, *args, noformat=noformat, **kwargs)

    return wrapper


@__loop_safe
def get_text(
    bot: "Anjani",
    chat_id: Optional[int],
    text_name: str,
    *args: Any,
    noformat: bool = False,
    **kwargs: Any,
) -> str:
    def _get_text(lang: str) -> str:
        try:
            text = codecs.decode(
                codecs.encode(bot.languages[lang][text_name], "latin-1", "backslashreplace"),
                "unicode-escape",
            )
        except KeyError:
            if lang == "en":
                return (
                    f"**NO LANGUAGE STRING FOR '{text_name}' in '{lang}'**\n"
                    "__Please forward this to__ @userbotindo"
                )

            bot.log.warning("NO LANGUAGE STRING FOR '%s' in '%s'", text_name, lang)
            return _get_text("en")
        else:
            try:
                return text if noformat else text.format(*args, **kwargs)
            except (IndexError, KeyError):
                bot.log.error("Failed to format '%s' string on '%s'", text_name, lang)
                raise

    return _get_text(bot.chats_languages.get(chat_id or 0, "en"))


# }
