import inspect
from functools import partial
from types import FunctionType
from typing import Any, Dict, Protocol, Tuple, Type, TypeVar, Union, runtime_checkable

from pyrogram import Client, types
from pyrogram.errors import PeerIdInvalid

from anjani.command import Context
from anjani.error import BadBoolArgument, ConversionError

__all__ = [
    "Converter",
    "UserConverter",
    "ChatConverter",
    "ChatMemberConverter",
    "parse_arguments",
]

T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class Converter(Protocol[T_co]):
    """Case class of custom converters that require the `~Context` to be passed.

    Class that derived this base converter need to have the `convert()`
    to do the conversion. This method should also be a `coroutine`.
    """

    async def convert(self, ctx: Context) -> T_co:
        """The base method that should be overided and will be called on conversion.

        Parameters:
            ctx (`~Context`):
                The invocation context that the client are currently used in.

        Raises:
            ConversionError: The converter failed to convert an argument.
        """
        raise NotImplementedError("Derived classes need to implement convert method!")


class UserConverter(Converter[types.User]):
    """Converts to a `~pyrogram.types.User`.

    Conversion priority:
    1. Using replied user.
    2. Using first argument user id.
    3. Using first argument mentioned user.
    4. Using the author that invoke the `~Context`.
    """

    async def extract_user(self, client: Client, user_ids: Union[str, int]) -> types.User:
        """Excract user from user id"""
        try:
            return await client.get_users(user_ids)
        except PeerIdInvalid as err:
            raise ConversionError(self, err) from err

    async def convert(self, ctx: Context) -> types.User:
        message = ctx.msg
        if message.reply_to_message:
            return message.reply_to_message.from_user
        if ctx.args:
            usr = ctx.args[0]
            if usr.isdigit():  # user_id
                return await self.extract_user(ctx.bot.client, int(usr))
            if usr.startswith("@"):  # username
                return await self.extract_user(ctx.bot.client, usr)
        return ctx.author


class ChatConverter(Converter[types.Chat]):
    """Converts to a `~pyrogram.types.ChatMember`.

    Conversion priority:
    1. Using first argument chat id.
    2. Using first argument chat username.
    3. Using the current invoked chat.
    """

    async def get_chat(self, client: Client, chat_ids: Union[int, str]) -> types.Chat:
        try:
            return await client.get_chat(chat_ids)
        except PeerIdInvalid as err:
            raise ConversionError(self, err) from err

    async def convert(self, ctx: Context) -> types.Chat:
        if ctx.args:
            chat = ctx.args[0]
            if (chat.startswith("-") and chat[1:].isdigit()) or chat.isdigit():
                return await self.get_chat(ctx.bot.client, int(chat))
            if chat.startswith("@"):
                return await self.get_chat(ctx.bot.client, chat)
        return ctx.chat


class ChatMemberConverter(Converter[types.ChatMember]):
    """Converts to a `~pyrogram.types.ChatMember`.

    Conversion priority:
    1. Using replied user.
    2. Using first argument user id.
    3. Using first argument username.
    """

    async def get_member(
        self, client: Client, chat_id: Union[int, str], user_id: Union[int, str]
    ) -> types.ChatMember:
        try:
            return await client.get_chat_member(chat_id, user_id)
        except PeerIdInvalid as err:
            raise ConversionError(self, err) from err

    async def convert(self, ctx: Context) -> types.ChatMember:
        chat = ctx.chat
        message = ctx.msg
        client = ctx.bot.client
        if message.reply_to_message:
            user = message.reply_to_message.from_user
            return await self.get_member(client, chat.id, user.id)
        if ctx.args:
            usr = ctx.args[0]
            if usr.isdigit():  # user_id
                return await self.get_member(client, chat.id, int(usr))
            if usr.startswith("@"):  # username
                return await self.get_member(client, chat.id, usr)
        return None


CONVERTER_MAP: Dict[Type[Any], Any] = {
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
    raise BadBoolArgument(arg)


def _get_default(param: inspect.Parameter, default=None) -> Union[Any, None]:
    return param.default if param.default is not param.empty else default


async def parse_arguments(sig: inspect.Signature, ctx: Context) -> Tuple[Any, ...]:
    message = ctx.msg
    args = []
    idx = 1
    items = iter(sig.parameters.items())
    next(items)  # skip Context argument
    for _, param in items:
        converter = param.annotation

        try:
            module = converter.__module__
        except AttributeError:
            pass
        else:
            if module is not None and module.startswith("pyrogram."):
                converter = CONVERTER_MAP.get(converter, converter)

        try:
            if converter is param.empty:
                res = message.command[idx]
            elif isinstance(converter, (FunctionType, partial)):
                if inspect.iscoroutinefunction(converter):
                    res = await converter(message.command[idx])
                else:
                    res = converter(message.command[idx])
            elif inspect.isclass(converter) and issubclass(converter, Converter):
                try:
                    res = await converter().convert(ctx) or _get_default(param)
                except ConversionError as err:
                    res = _get_default(param, err)
            else:
                if converter is bool:
                    try:
                        res = _bool_converter(message.command[idx])
                    except BadBoolArgument as err:
                        res = _get_default(param, err)
                else:
                    res = converter(message.command[idx])
        except IndexError:
            res = _get_default(param)
        idx += 1
        args.append(res)
    return tuple(args)
