"""Bot custon filters"""

import re
import shlex
from typing import Union, List

from pyrogram.filters import create
from pyrogram.types import Message


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
