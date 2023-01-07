"""Anjani converter"""
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

import inspect
from functools import partial
from types import FunctionType
from typing import Any, Dict, List, MutableMapping, Optional, Tuple, Type, Union

from pyrogram import types
from pyrogram.client import Client
from pyrogram.errors import PeerIdInvalid

from anjani.command import CommandFunc, Context
from anjani.error import BadArgument, BadBoolArgument, BadResult, ConversionError

__all__ = [
    "Converter",
    "UserConverter",
    "ChatConverter",
    "ChatMemberConverter",
    "parse_arguments",
]


class Converter:
    """Base class of custom converters that require the `~Context` to be passed.

    Class that derived this base converter need to have the `__call__`
    to do the conversion. This method should also be a `coroutine`.
    """

    async def __call__(self, ctx: Context, arg: str) -> None:  # skipcq: PYL-W0613
        """The base method that should be overrided and will be called on conversion.

        Parameters:
            ctx (`~Context`): The command invocation context that the argument used in.
            arg (`str`): The argument that is being converted.

        Raises:
            ConversionError: The converter failed to convert an argument.
        """
        raise NotImplementedError("Derived classes need to implement __call__ method!")


class EntityConverter(Converter):  # skipcq: PYL-W0223
    @staticmethod
    def parse_entities(msg: types.Message, arg: str) -> Optional[types.User]:
        for i in msg.entities:
            if i.type == "text_mention" and msg.text[i.offset : i.offset + i.length] == arg:
                return i.user
        return None


class UserConverter(EntityConverter):
    """Converts to a `~pyrogram.types.User`.

    Conversion priority:
    1. By user id.
    2. By username.
    3. By text mention.
    """

    async def extract_user(self, client: Client, user_id: Union[str, int]) -> types.User:
        """Excract user from user id"""
        try:
            user = await client.get_users(user_id)
            if isinstance(user, types.User):
                return user

            raise BadResult(f"Invalid conversion types '{type(user)}' result")
        except PeerIdInvalid as err:
            raise ConversionError(self, err) from err

    async def __call__(self, ctx: Context, arg: str) -> Optional[types.User]:
        if arg.isdigit() or arg.startswith("@"):
            try:
                user = await ctx.bot.client.get_users(arg)
                if isinstance(user, types.User):
                    return user

                raise BadResult(f"Invalid conversion types '{type(user)}' result")
            except PeerIdInvalid as err:
                raise ConversionError(self, err) from err
        return self.parse_entities(ctx.msg, arg)


class ChatConverter(Converter):
    """Converts to a `~pyrogram.types.ChatMember`.

    Conversion priority:
    1. By chat id.
    2. By chat username (with '@').
    3. By chat username (without '@').
    """

    async def __call__(self, ctx: Context, args: str) -> types.Chat:
        try:
            chat = await ctx.bot.client.get_chat(args)
            if isinstance(chat, types.Chat):
                return chat

            raise BadResult(f"Invalid conversion types `{type(chat)}` result")
        except PeerIdInvalid as err:
            raise ConversionError(self, err) from err


class ChatMemberConverter(EntityConverter):
    """Converts to a `~pyrogram.types.ChatMember`.

    Conversion priority:
    1. By user id.
    2. By username.
    3. By text mention.
    """

    async def get_member(
        self, client: Client, chat_id: int, user_id: Union[int, str]
    ) -> types.ChatMember:
        try:
            return await client.get_chat_member(chat_id, user_id)
        except PeerIdInvalid as err:
            raise ConversionError(self, err) from err

    async def __call__(self, ctx: Context, arg: str) -> Optional[types.ChatMember]:
        if arg.isdigit() or arg.startswith("@"):
            return await self.get_member(ctx.bot.client, ctx.chat.id, arg)
        res = self.parse_entities(ctx.msg, arg)
        if res:
            return await self.get_member(ctx.bot.client, ctx.chat.id, res.id)

        return None


CONVERTER_MAP: MutableMapping[Type[Any], Any] = {
    types.User: UserConverter,
    types.Chat: ChatConverter,
    types.ChatMember: ChatMemberConverter,
}


def _bool_converter(arg: str) -> Union[bool, BadBoolArgument]:
    arg = arg.lower()
    if arg in ("yes", "true", "enable", "on", "1"):
        return True
    if arg in ("no", "false", "disable", "off", "0"):
        return False
    raise BadBoolArgument(f"Unrecognized argument of boolean '{arg}'")


def _get_default(param: inspect.Parameter, default: Any = None) -> Union[Any, None]:
    return param.default if param.default is not param.empty else default


async def transform(ctx: Context, param: inspect.Parameter, arg: str) -> Any:
    converter = param.annotation

    if converter is param.empty:
        return arg

    # Check if the annotation was an `Optional` or `Union` type.
    # This type hinting make a parsing ambiguities.
    # Hence we just simply use the first arg as the converter if is not None type.
    # Else use the second arg.
    if getattr(converter, "__origin__", None) is Union:
        if converter.__args__[0] is None:
            converter = converter.__args__[1]
        else:
            converter = converter.__args__[0]

    if isinstance(converter, (FunctionType, partial)):
        if inspect.iscoroutinefunction(converter):
            return await converter(arg)

        return converter(arg)

    try:
        module = converter.__module__
    except AttributeError:
        pass
    else:
        if module is not None and module.startswith("pyrogram."):
            converter = CONVERTER_MAP.get(converter, converter)

    if inspect.isclass(converter) and issubclass(converter, Converter):
        try:
            return await converter()(ctx, arg)
        except ConversionError as err:
            return _get_default(param, err)

    if converter is bool:
        try:
            return _bool_converter(arg)
        except BadBoolArgument as err:
            return _get_default(param, err)

    try:
        return converter(arg)
    except ValueError as err:
        return _get_default(param, err)


async def parse_arguments(
    sig: inspect.Signature, ctx: Context, func: CommandFunc
) -> Tuple[List[Any], Dict[Any, Any]]:
    to_convert = ctx.args
    args = []  # type: List[Any]
    kwargs = {}  # type: Dict[Any, Any]
    idx = 0
    items = iter(sig.parameters.items())

    # skip Context argument
    next(items)  # skipcq: PTC-W0063
    for name, param in items:
        if param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY):
            try:
                result = await transform(ctx, param, to_convert[idx])
            except IndexError:
                result = _get_default(param)
            args.append(result)
            idx += 1
        elif param.kind == param.KEYWORD_ONLY:
            # Consume remaining text to the kwargs
            kwargs[name] = " ".join(to_convert[idx:]).strip()
            break
        elif param.kind in {param.VAR_POSITIONAL, param.VAR_KEYWORD}:
            raise BadArgument(
                f"Unsuported {param.kind} parameter conversion "
                f"Found '*{name}' on '{func.__name__}'"
            )
    return args, kwargs
