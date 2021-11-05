"""Anjani base command"""
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

import asyncio
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Coroutine,
    Iterable,
    Optional,
    Sequence,
    Union,
)

import pyrogram
from pyrogram.filters import Filter
from typing_extensions import final

from anjani.action import BotAction
from anjani.util.tg import get_text
from anjani.util.types import CustomFilter

if TYPE_CHECKING:
    from anjani.core import Anjani

CommandFunc = Union[
    Callable[..., Coroutine[Any, Any, None]], Callable[..., Coroutine[Any, Any, Optional[str]]]
]
Decorator = Callable[[CommandFunc], CommandFunc]


def filters(_filters: Optional[Filter] = None, *, aliases: Iterable[str] = []) -> Decorator:
    """Sets filters on a command function."""

    def filter_decorator(func: CommandFunc) -> CommandFunc:
        setattr(func, "_cmd_filters", _filters)
        setattr(func, "_cmd_aliases", aliases)
        return func

    return filter_decorator


class Command:
    name: str
    plugin: Any
    func: Union[CommandFunc, CommandFunc]
    filters: Optional[Union[Filter, CustomFilter]]
    aliases: Iterable[str]

    def __init__(
        self,
        name: str,
        plugin: Any,
        func: CommandFunc,
        cmdFilter: Optional[Union[Filter, CustomFilter]],
        aliases: Iterable[str],
    ) -> None:
        self.name = name
        self.plugin = plugin
        self.func = func
        self.filters = cmdFilter
        self.aliases = aliases

    def __repr__(self) -> str:
        return f"<command plugin '{self.name}' from '{self.plugin.name}'>"


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
    input_raw: str
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
        slices = self.cmd_len + 1 + len(username)
        if username in self.msg.text:
            self.input = self.msg.text[slices:]
            self.input_raw = self.msg.text.markdown[slices:]
        else:
            self.input = self.msg.text[self.cmd_len :]
            self.input_raw = self.msg.text.markdown[self.cmd_len :]

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

            async def delete(delay: float) -> None:
                await asyncio.sleep(delay)
                await content.delete(True)

            self.bot.loop.create_task(delete(delay))
        else:
            await content.delete(True)

    async def respond(
        self,
        text: str = "",
        *,
        animation: Optional[Union[str, BinaryIO, IO[bytes]]] = None,
        audio: Optional[Union[str, BinaryIO, IO[bytes]]] = None,
        document: Optional[Union[str, BinaryIO, IO[bytes]]] = None,
        photo: Optional[Union[str, BinaryIO, IO[bytes]]] = None,
        video: Optional[Union[str, BinaryIO, IO[bytes]]] = None,
        delete_after: Optional[Union[int, float]] = None,
        mode: str = "edit",
        redact: bool = True,
        reference: Optional[pyrogram.types.Message] = None,
        **kwargs: Any,
    ) -> Optional[pyrogram.types.Message]:
        """Respond to the destination with the content given.

        Parameters:
            text (`str`, *Optional*):
                Text of the message to be sent.
                *Optional* only if either :obj:`animation`, :obj:`audio`, :obj:`document`,
                :obj:`photo`, :obj:`video` or :obj:`delete_after` is provided.

            annimation (`str` | `BinaryIO`, *Optional*):
                Annimation to send. Pass a file_id as string to send an animation(GIF) file that
                exists on the Telegram servers, pass an HTTP URL as a string for Telegram
                to get an animation file from the Internet, pass a file path as string to upload
                a new animation file that exists on your local machine, or pass a binary
                file-like object with its attribute “.name” set for in-memory uploads.

            audio (`str` | `BinaryIO`, *Optional*):
                Audio file to send. Pass a file_id as string to send an audio file that
                exists on the Telegram servers, pass an HTTP URL as a string for Telegram
                to get an audio file from the Internet, pass a file path as string to upload
                a new audio file that exists on your local machine, or pass a binary
                file-like object with its attribute “.name” set for in-memory uploads.

            document (`str` | `BinaryIO`, *Optional*):
                File to send. Pass a file_id as string to send a file that exists on the
                Telegram servers, pass an HTTP URL as a string for Telegram to get a file
                from the Internet, pass a file path as string to upload a new file that
                exists on your local machine, or pass a binary file-like object with its
                attribute “.name” set for in-memory uploads.

            photo (`str` | `BinaryIO`, *Optional*):
                Photo to send. Pass a file_id as string to send a photo that exists on the
                Telegram servers, pass an HTTP URL as a string for Telegram to get a photo
                from the Internet, pass a file path as string to upload a new photo that
                exists on your local machine, or pass a binary file-like object with its
                attribute “.name” set for in-memory uploads.

            video (`str` | `BinaryIO`, *Optional*):
                Video to send. Pass a file_id as string to send a video that exists on the
                Telegram servers, pass an HTTP URL as a string for Telegram to get a video
                from the Internet, or pass a file path as string to upload a new video that
                exists on your local machine.

            delete_after (`float`, *Optional*):
                If provided, the number of seconds to wait in the background before deleting
                the message we just sent. If the deletion fails, then it is silently ignored.

            mode (`str`, *Optional*):
                The mode that the client will respond. "edit" and "reply". defaults to "edit".

            redact (`bool`, *Optional*):
                Tells wether the text will be redacted from sensitive environment key.
                Defaults to `True`.

            reference (`pyrogram.types.Message`, *Optional*):
                Tells client which message to respond (message to edit or to reply based on mode).
        """
        self.response = await self.bot.respond(
            reference or self.msg,
            text,
            mode=mode,
            redact=redact,
            response=self.response,
            animation=animation,
            audio=audio,
            document=document,
            photo=photo,
            video=video,
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
                *"choose_contact"* for contacts, *"playing"* for games, *"speaking"* for speaking in group calls.
        """
        return BotAction(self, action)

    @final
    def get_text(
        self, text_name: str, *args: Any, noformat: bool = False, **kwargs: Any
    ) -> Coroutine[Any, Any, str]:
        """Bound method *get_text* of :obj:`~Anjani.plugin.Plugin`.

        Parse the string with user language setting.

        Parameters:
            text_name (`str`):
                String name to parse. The string is parsed from YAML documents.
            *args (`any`, *Optional*):
                One or more values that should be formatted and inserted in the string.
                The value should be in order based on the language string placeholder.
            noformat (`bool`, *Optional*):
                If exist and True, the text returned will not be formated.
                Default to False.
            **kwargs (`any`, *Optional*):
                One or more keyword values that should be formatted and inserted in the string.
                based on the keyword on the language strings.
        """
        return get_text(self.bot, self.chat.id, text_name, *args, noformat=noformat, **kwargs)
