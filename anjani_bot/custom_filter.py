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
# pylint: disable=W0212, C0103

import logging
import re
import shlex
from typing import List, Union

from pyrogram.errors import ChannelPrivate
from pyrogram.filters import create
from pyrogram.types import Message

from .utils import adminlist

LOGGER = logging.getLogger(__name__)


def command(commands: Union[str, List[str]], case_sensitive: bool = False):
    """Build a command that accept bot username eg: /start@AnjaniBot"""

    async def func(flt, client, message: Message):
        text: str = message.text or message.caption
        message.command: List[str] = []

        if not text:
            return False

        regex = r"^/(\w+)(@{username})?(?: |$)(.*)".format(username=client.__bot__.username)
        matches = re.compile(regex).search(text)

        if matches:
            if matches.group(1) not in flt.commands:
                return False
            if matches.group(3) == "":
                return True
            try:
                for arg in shlex.split(matches.group(3)):
                    message.command.append(arg)
            except ValueError:
                pass
            return True
        return False

    commands = commands if isinstance(commands, list) else [commands]
    commands = {c if case_sensitive else c.lower() for c in commands}

    return create(func, "CustomCommandFilter", commands=commands, case_sensitive=case_sensitive)


async def _admin_filters(_, client, message: Message) -> bool:
    if message.chat.type != "private":
        chat_id = message.chat.id
        user_id = message.from_user.id
        return bool(
            user_id in await adminlist(client, chat_id) or user_id in client.__bot__.staff_id
        )
    return False


async def _bot_admin_filters(_, client, message: Message) -> bool:
    if message.chat.type != "private":
        bot = await client.get_chat_member(message.chat.id, "me")
        if bot.status == "administrator":
            return True
        await message.reply_text("I'm not an admin")
    return False


async def _staff_filters(_, client, message: Message) -> bool:
    user_id = message.from_user.id
    return bool(user_id in client.__bot__.staff_id)


async def staff_rank(flt, client, message: Message) -> bool:
    """Check staff rank"""
    user_id = message.from_user.id
    if flt.rank == "owner":
        return bool(user_id == client.__bot__.staff.get("owner"))
    if flt.rank == "dev":
        return bool(
            user_id in client.__bot__.staff.get("dev")
            or user_id == client.__bot__.staff.get("owner")
        )
    LOGGER.error(f"Unknown rank '{flt.rank}'! Avalaible rank ['owner', 'dev']")
    return False


async def check_perm(flt, client, message: Message) -> bool:
    """Check user and bot permission"""
    chat_id = message.chat.id
    # Check Chat type first
    if message.chat.type == "private":
        await message.reply_text(await client.__bot__.text(chat_id, "error-chat-private"))
        return False
    try:
        bot = await client.get_chat_member(chat_id, "me")
        user = await client.get_chat_member(chat_id, message.from_user.id)
    except (ChannelPrivate, AttributeError) as err:
        LOGGER.warning(f"Failed getting chat member of:\n{message}\n{err}")
        return False
    perm = True

    if flt.can_change_info and not (bot.can_change_info and user.can_change_info):
        perm = False
    elif flt.can_delete and not (bot.can_delete_messages and user.can_delete_messages):
        perm = False
    elif flt.can_restrict and not (
        bot.can_restrict_members and (user.can_restrict_members or user in client.__bot__.staff_id)
    ):
        perm = False
    elif flt.can_invite_users and not (bot.can_invite_users and user.can_invite_users):
        perm = False
    elif flt.can_pin and not (bot.can_pin_messages and user.can_pin_messages):
        perm = False
    elif flt.can_promote and not (
        bot.can_promote_members and (user.can_promote_members or user in client.__bot__.staff_id)
    ):
        perm = False

    return perm


admin = create(_admin_filters)
bot_admin = create(_bot_admin_filters)
staff = create(_staff_filters)
