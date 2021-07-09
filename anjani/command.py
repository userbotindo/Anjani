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
from pyrogram.filters import Filter, AndFilter, OrFilter, InvertFilter

from anjani.custom_filter import CustomFilter

if TYPE_CHECKING:
    from .core import Anjani

CommandFunc = Union[Callable[..., Coroutine[Any, Any, None]],
                    Callable[..., Coroutine[Any, Any, Optional[str]]]]
Decorator = Callable[[CommandFunc], CommandFunc]


def check_filters(filters: Union[Filter, CustomFilter], anjani: "Anjani") -> None:
    """ Recursively check filters to apply anjani object into CustomFilter instance"""
    if isinstance(filters, (AndFilter, OrFilter, InvertFilter)):
        check_filters(filters.base, anjani)
    if isinstance(filters, (AndFilter, OrFilter)):
        check_filters(filters.other, anjani)

    include_bot = getattr(filters, "include_bot", False)
    # Because only (currently) :obj:`~CustomFilter` are needed the :obj:`~Anjani`
    if include_bot and isinstance(filters, CustomFilter):
        filters.anjani = anjani


def filters(filters: Filter) -> Decorator:
    """Sets filters on a command function."""

    def filter_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_filters", filters)
        return func

    return filter_decorator


class Command:
    name: str
    filters: Optional[Union[Filter, CustomFilter]]
    plugin: Any
    func: CommandFunc

    def __init__(self, name: str, plugin: Any, func: CommandFunc) -> None:
        self.name = name
        self.filters = getattr(func, "_cmd_filters", None)
        self.plugin = plugin
        self.func = func

        if self.filters:
            check_filters(self.filters, self.plugin.bot)


# Command invocation context
class Context:
    bot: "Anjani"
    msg: pyrogram.types.Message
    cmd_len: int

    response: pyrogram.types.Message
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
        self.response = None  # type: ignore
        # Single argument string
        username = self.bot.user.username
        if username in self.msg.text:
            self.input = self.msg.text[self.cmd_len + len(username) :]
        else:
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