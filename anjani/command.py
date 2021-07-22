import asyncio
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional, Sequence, Union

import pyrogram
from pyrogram.filters import AndFilter, Filter, InvertFilter, OrFilter

from anjani.action import BotAction
from anjani.custom_filter import CustomFilter

if TYPE_CHECKING:
    from .core import Anjani

CommandFunc = Union[
    Callable[..., Coroutine[Any, Any, None]], Callable[..., Coroutine[Any, Any, Optional[str]]]
]
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
    author: pyrogram.types.User
    bot: "Anjani"
    chat: pyrogram.types.Chat
    msg: pyrogram.types.Message
    message: pyrogram.types.Message
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
        self.cmd_len = cmd_len
        self.msg = self.message = msg
        self.author = msg.from_user
        self.chat = msg.chat

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

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # Argument segments
    def _get_args(self) -> Sequence[str]:
        self.args = self.segments[1:]
        return self.args

    async def delete(
        self, delay: Optional[float] = None, message: Optional[pyrogram.types.Message] = None
    ) -> None:
        """Bound method of *delete* of :obj:`~pyrogram.types.Message`.
        If the deletion fails then it is silently ignored.

        delay (`float`, *optional*):
            If provided, the number of seconds to wait in the background
            before deleting the message.
        message (`~pyrogram.types.Message`, *optional*):
            If provided, the message passed will be deleted else will delete
            the client latest response.
        """
        content = message or self.response
        if not content:
            return

        if delay:

            async def delete(delay: float):
                await asyncio.sleep(delay)
                await content.delete(True)

            asyncio.create_task(delete(delay))
        else:
            await content.delete(True)

    # Wrapper for Bot.respond()
    async def respond(
        self,
        text: str,
        *,
        delete_after: Optional[float] = None,
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
        if delete_after:
            await self.delete(delete_after)
            self.response = None  # type: ignore
        return self.response

    async def trigger_action(self, action: str = "typing") -> bool:
        """Triggers a ChatAction on the invoked chat.
        A Shortcut for *bot.client.send_chat_action()*

        Parameters:
            action (`str`, *Optional*):
                Type of action to broadcast. Choose one, depending on what the user is about to receive: *"typing"* for
                text messages, *"upload_photo"* for photos, *"record_video"* or *"upload_video"* for videos,
                *"record_audio"* or *"upload_audio"* for audio files, *"upload_document"* for general files,
                *"find_location"* for location data, *"record_video_note"* or *"upload_video_note"* for video notes,
                *"choose_contact"* for contacts, *"playing"* for games, *"speaking"* for speaking in group calls or
                *"cancel"* to cancel any chat action currently displayed.
        """
        return await self.bot.client.send_chat_action(self.chat.id, action)

    def action(self, action: str = "typing") -> BotAction:
        """Returns a context manager that allows you to send a chat action
        for an indefinite time.

        Parameters:
            action (`str`, *Optional*):
                Type of action to broadcast. Choose one, depending on what the user is about to receive: *"typing"* for
                text messages, *"upload_photo"* for photos, *"record_video"* or *"upload_video"* for videos,
                *"record_audio"* or *"upload_audio"* for audio files, *"upload_document"* for general files,
                *"find_location"* for location data, *"record_video_note"* or *"upload_video_note"* for video notes,
                *"choose_contact"* for contacts, *"playing"* for games, *"speaking"* for speaking in group calls or
                *"cancel"* to cancel any chat action currently displayed.
        """
        return BotAction(self, action)
