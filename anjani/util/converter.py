import inspect
from functools import partial
from types import FunctionType
from typing import (
    Any,
    Callable,
    Dict,
    List,
    MutableMapping,
    Optional,
    Tuple,
    Type,
    Union,
)

from pyrogram import Client, types
from pyrogram.errors import PeerIdInvalid

from anjani.command import Context
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

    Attribute:
        skip (`bool`):
            if the value is True. The converter will not consume any argument from the message text.
            Hence the argument can be used for the next converter.
    """

    skip: bool = False

    async def __call__(self, ctx: Context) -> None:  # skipcq: PYL-W0613
        """The base method that should be overided and will be called on conversion.

        Parameters:
            ctx (`~Context`):
                The invocation context that the client are currently used in.

        Raises:
            ConversionError: The converter failed to convert an argument.
        """
        raise NotImplementedError("Derived classes need to implement __call__ method!")


class EntityConverter(Converter):
    @staticmethod
    def parse_entities(msg: types.Message) -> Optional[Union[types.User, str]]:
        for i in msg.entities:
            if i.type == "mention":
                return msg.text[i.offset : i.offset + i.length]
            if i.type == "text_mention":
                return i.user
        return None


class UserConverter(EntityConverter):
    """Converts to a `~pyrogram.types.User`.

    Conversion priority:
    1. Using replied user.
    2. Using first argument user id.
    3. Using first argument mentioned user.
    4. Using any mention available on the message.
    5. Using any text mention available on the message.
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

    async def __call__(self, ctx: Context) -> Optional[types.User]:
        message = ctx.msg
        if message.reply_to_message:
            self.skip = True
            return message.reply_to_message.from_user

        if ctx.args:  # lookup basic text
            usr = ctx.args[0]
            if usr.isdigit():  # user_id
                return await self.extract_user(ctx.bot.client, int(usr))
            if usr.startswith("@"):  # username
                return await self.extract_user(ctx.bot.client, usr)

        if message.entities:  # lookup mentioned user in message entities
            res = self.parse_entities(message)
            if isinstance(res, types.User):
                return res
            if res is not None:
                return await self.extract_user(ctx.bot.client, res)

        self.skip = True


class ChatConverter(Converter):
    """Converts to a `~pyrogram.types.ChatMember`.

    Conversion priority:
    1. Using first argument chat id.
    2. Using first argument chat username.
    3. Using the current invoked chat.
    """

    async def get_chat(self, client: Client, chat_ids: Union[int, str]) -> types.Chat:
        try:
            chat = await client.get_chat(chat_ids)
            if isinstance(chat, types.Chat):
                return chat

            raise BadResult(f"Invalid conversion types '{type(chat)}' result")
        except PeerIdInvalid as err:
            raise ConversionError(self, err) from err

    async def __call__(self, ctx: Context) -> types.Chat:
        if ctx.args:
            chat = ctx.args[0]
            if (chat.startswith("-") and chat[1:].isdigit()) or chat.isdigit():
                return await self.get_chat(ctx.bot.client, int(chat))
            if chat.startswith("@"):
                return await self.get_chat(ctx.bot.client, chat)
        return ctx.chat


class ChatMemberConverter(EntityConverter):
    """Converts to a `~pyrogram.types.ChatMember`.

    Conversion priority:
    1. Using replied user.
    2. Using first argument user id.
    3. Using first argument mentioned user.
    4. using mention.
    5. Using text mention.
    6. Using the author that invoke the `~Context`.
    """

    async def get_member(
        self, client: Client, chat_id: Union[int, str], user_id: Union[int, str]
    ) -> types.ChatMember:
        try:
            return await client.get_chat_member(chat_id, user_id)
        except PeerIdInvalid as err:
            raise ConversionError(self, err) from err

    async def __call__(self, ctx: Context) -> types.ChatMember:
        chat = ctx.chat
        message = ctx.msg
        client = ctx.bot.client
        if message.reply_to_message:
            self.skip = True
            user = message.reply_to_message.from_user
            return await self.get_member(client, chat.id, user.id)

        if ctx.args:  # lookup basic text
            usr = ctx.args[0]
            if usr.isdigit():  # user_id
                return await self.get_member(client, chat.id, int(usr))
            if usr.startswith("@"):  # username
                return await self.get_member(client, chat.id, usr)

        if message.entities:  # lookup mentioned user in message entities
            res = self.parse_entities(message)
            if isinstance(res, types.User):
                return await self.get_member(client, chat.id, res.id)
            if res is not None:
                return await self.get_member(client, chat.id, res)

        self.skip = True
        return await self.get_member(client, chat.id, ctx.author.id)


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


async def transform(ctx: Context, param: inspect.Parameter, idx: int) -> Tuple[Any, bool]:
    message = ctx.message
    converter = param.annotation

    if converter is param.empty:
        return message.command[idx], False

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
            return await converter(message.command[idx]), False
        else:
            return converter(message.command[idx]), False

    try:
        module = converter.__module__
    except AttributeError:
        pass
    else:
        if module is not None and module.startswith("pyrogram."):
            converter = CONVERTER_MAP.get(converter, converter)
    if inspect.isclass(converter) and issubclass(converter, Converter):
        try:
            conv = converter()
            result = await conv(ctx)
            if result:
                return result, conv.skip
            return _get_default(param), False
        except ConversionError as err:
            return _get_default(param, err), False

    if converter is bool:
        try:
            return _bool_converter(message.command[idx]), False
        except BadBoolArgument as err:
            return _get_default(param, err), False

    return converter(message.command[idx]), False


async def parse_arguments(
    sig: inspect.Signature, ctx: Context, func: Callable[[Any], Any]
) -> Tuple[List[Any], Dict[Any, Any]]:
    message = ctx.msg
    args = []  # type: List[Any]
    kwargs = {}  # type: Dict[Any, Any]
    idx = 1
    items = iter(sig.parameters.items())
    next(items)  # skip Context argument
    for name, param in items:
        if param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY):
            try:
                result, reply = await transform(ctx, param, idx)
            except IndexError:
                reply = False
                result = _get_default(param)
            args.append(result)
            if not reply:
                idx += 1
        elif param.kind == param.KEYWORD_ONLY:
            # Consume remaining text to the kwargs
            kwargs[name] = " ".join(message.command[idx:]).strip()
            break
        elif param.kind == param.VAR_POSITIONAL:
            raise BadArgument(
                "Unsuported Variable Positional Argument conversion "
                f"Found '*{name}' on '{func.__name__ }'"
            )
    return args, kwargs
