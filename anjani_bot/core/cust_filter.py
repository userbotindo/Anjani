"""Bot custon filters"""
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

# pylint: disable=unsubscriptable-object
import re
import shlex
from typing import Union, List, Optional

from pyrogram.filters import create
from pyrogram.types import Message

from ..utils import adminlist


def command(commands: Union[str, List[str]],
            prefixes: Optional[Union[str, List[str]]] = "/",
            case_sensitive: bool = False):
    """Build a command that accept bot username eg: /start@AnjaniBot"""

    async def func(flt, client, message: Message):
        text: str = message.text or message.caption
        message.command: List[str] = list()

        if not text:
            return False

        regex = "^{prefix}+\\b{regex}\\b(\\b@{bot_name}\\b)?(.*)".format(
            prefix="|".join(re.escape(x) for x in prefixes),
            regex="|".join(flt.commands).lower(),
            bot_name=client.username.lower(),
        )

        matches = re.compile(regex).match(text.lower())

        if matches:
            if matches.group(1) is None and matches.group(2).startswith("@"):
                return False
            for arg in shlex.split(matches.group(2)):
                message.command.append(arg)
            return True
        return False

    commands = commands if isinstance(commands, list) else [commands]
    commands = {c if case_sensitive else c.lower() for c in commands}

    prefixes = [] if isinstance(prefixes, type(None)) else prefixes
    prefixes = prefixes if isinstance(prefixes, list) else [prefixes]
    prefixes = set(prefixes) if prefixes else {""}

    return create(
        func,
        "CustomCommandFilter",
        commands=commands,
        prefixes=prefixes,
        case_sensitive=case_sensitive
    )


async def _admin_filters(_, client, message: Message) -> bool:
    if message.chat.type != "private":
        chat_id = message.chat.id
        user_id = message.from_user.id
        return bool(
            user_id in await adminlist(client, chat_id)
            or user_id in client.staff_id
        )
    return False


async def _bot_admin_filters(_, client, message: Message) -> bool:
    if message.chat.type != "private":
        bot = await client.get_chat_member(message.chat.id, 'me')
        if bot.status == "administrator":
            return True
        await message.reply_text("I'm not an admin")
    return False


async def _staf_filters(_, client, message: Message) -> bool:
    user_id = message.from_user.id
    return bool(user_id in client.staff_id)

# pylint: disable=invalid-name
admin = create(_admin_filters)
bot_admin = create(_bot_admin_filters)
staff = create(_staf_filters)
