from typing import (
    Optional,
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Sequence,
    Union,
)

import pyrogram
from pyrogram.filters import Filter

if TYPE_CHECKING:
    from .core import Anjani

CommandFunc = Union[Callable[..., Coroutine[Any, Any, None]],
                    Callable[..., Coroutine[Any, Any, Optional[str]]]]
Decorator = Callable[[CommandFunc], CommandFunc]


def desc(_desc: str) -> Decorator:
    """Sets description on a command function."""

    def desc_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_description", _desc)
        return func

    return desc_decorator


def usage(_usage: str,
          optional: bool = False,
          reply: bool = False) -> Decorator:
    """Sets argument usage help on a command function."""

    def usage_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_usage", _usage)
        setattr(func, "_cmd_usage_optional", optional)
        setattr(func, "_cmd_usage_reply", reply)
        return func

    return usage_decorator


def alias(*aliases: str) -> Decorator:
    """Sets aliases on a command function."""

    def alias_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_aliases", aliases)
        return func

    return alias_decorator


def filters(_filters: Filter) -> Decorator:
    """Sets filters on a command function."""

    def filter_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_filters", _filters)
        return func

    return filter_decorator


class Command:
    name: str
    desc: Optional[str]
    usage: Optional[str]
    usage_optional: bool
    usage_reply: bool
    aliases: Sequence[str]
    filters: Optional[Filter]
    plugin: Any
    run: CommandFunc

    def __init__(self, name: str, plugin: Any, func: CommandFunc) -> None:
        self.name = name
        self.desc = getattr(func, "_cmd_description", None)
        self.usage = getattr(func, "_cmd_usage", None)
        self.usage_optional = getattr(func, "_cmd_usage_optional", False)
        self.usage_reply = getattr(func, "_cmd_usage_reply", False)
        self.aliases = getattr(func, "_cmd_aliases", [])
        self.filters = getattr(func, "_cmd_filters", None)
        self.plugin = plugin
        self.run = func


# Command invocation context
class Context:
    bot: "Anjani"
    msg: pyrogram.types.Message
    cmd_len: int

    response: Optional[pyrogram.types.Message]
    input: str
    args: Sequence[str]

    segments: Sequence[str]
    invoker: str

    def __init__(
        self,
        bot: "Anjani",
        msg: pyrogram.types.Message,
        cmd_len: int,
    ) -> None:
        self.bot = bot
        self.msg = msg
        self.cmd_len = cmd_len

        # Response message to be filled later
        self.response = None
        # Single argument string (unparsed, i.e. complete with Markdown formatting symbols)
        self.input = self.msg.text[self.cmd_len :]

        self.segments = self.msg.command
        self.invoker = self.segments[0]

    # Lazily resolve expensive fields
    def __getattr__(self, name: str) -> Any:
        if name == "args":
            return self._get_args()

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    # Argument segments
    def _get_args(self) -> Sequence[str]:
        self.args = self.segments[1:]
        return self.args

    # Wrapper for Bot.respond()
    async def respond(
        self,
        text: str,
        *,
        mode: str = "edit",
        redact: bool = True,
        msg: Optional[pyrogram.types.Message] = None,
        **kwargs: Any,
    ) -> Optional[pyrogram.types.Message]:

        self.response = await self.bot.respond(
            msg or self.msg,
            text,
            mode=mode,
            redact=redact,
            response=self.response,
            **kwargs,
        )
        return self.response