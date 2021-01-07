"""Bot custon filters"""

import re
import shlex
from typing import Union, List

from pyrogram.filters import create
from pyrogram.types import Message

from .. import Config
from ..utils import adminlist



def command(commands: Union[str, List[str]],
            prefixes: Union[str, List[str]] = "/",
            case_sensitive: bool = False):
    """Build a command that accept bot username eg: /start@NekoBot"""

    async def func(flt, _, message: Message):
        text: str = message.text or message.caption
        message.command = []

        me = await _.get_me()  # pylint: disable=invalid-name

        if not text:
            return False

        regex = "^({prefix})+\\b({regex})\\b(\\b@{bot_name}\\b)?(.*)".format(
            prefix="|".join(re.escape(x) for x in prefixes),
            regex="|".join(flt.commands).lower(),
            bot_name=me.username,
        )

        matches = re.search(re.compile(regex), text.lower())
        if matches:
            for arg in shlex.split(matches.group(4).strip()):
                if arg.startswith("@") and arg != f"@{me.username.lower()}":
                    return False
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
    chat_id = message.chat.id
    user_id = message.from_user.id
    admin_list = await adminlist(client, chat_id)
    if user_id in admin_list:
        return True
    if user_id == Config.OWNER_ID:
        return True
    if Config.SUDO_USERS and user_id in Config.SUDO_USERS:
        return True
    return False


async def _staf_filters(_, __, message: Message) -> bool:
    user_id = message.from_user.id
    if user_id == Config.OWNER_ID:
        return True
    if Config.SUDO_USERS and user_id in Config.SUDO_USERS:
        return True
    return False

# pylint: disable=invalid-name
admin = create(_admin_filters)
staff = create(_staf_filters)
