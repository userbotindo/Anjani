import codecs
import inspect
import logging
import os.path
from asyncio.tasks import run_coroutine_threadsafe
from functools import wraps
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Protocol

from anjani import util

if TYPE_CHECKING:
    from .core import Anjani


class Func(Protocol):
    def __call__(
        _self, self: "Plugin", chat_id: int, text_name: str, *args: Any, **kwargs: Any
    ) -> str:
        ...


def loop_safe(func: Func):  # Let default typing choose the return type
    """ Decorator for text methods """

    @wraps(func)
    async def wrapper(
        self: "Plugin", chat_id: int, text_name: str, *args: Any, **kwargs: Any
    ) -> str:
        return await util.run_sync(func, self, chat_id, text_name, *args, **kwargs)

    return wrapper


class Plugin:
    # Class variables
    name: ClassVar[str] = "Unnamed"
    disabled: ClassVar[bool] = False
    helpable: ClassVar[bool] = False

    # Instance variables
    bot: "Anjani"
    log: logging.Logger
    comment: Optional[str]

    def __init__(self, bot: "Anjani") -> None:
        self.bot = bot
        self.log = logging.getLogger(type(self).name.lower().replace(" ", "_"))
        self.comment = None

    @loop_safe
    def text(
        self,
        chat_id: int,
        text_name: str,
        *args: Any,
        noformat: bool = False,
        _recurse: bool = False,
        **kwargs: Any,
    ) -> str:
        """Parse the string with user language setting.
        Parameters:
            chat_id (`int`):
                Id of the sender(PM's) or chat_id to fetch the user language setting.
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
        if _recurse:
            data = "en"
        else:
            data = self.bot.chats_languages.get(chat_id, "en")

        try:
            if data in self.bot.languages and text_name in self.bot.languages[data]:
                text = codecs.decode(
                    codecs.encode(
                        self.bot.languages[data][text_name], "latin-1", "backslashreplace"
                    ),
                    "unicode-escape",
                )
                return text if noformat else text.format(*args, **kwargs)
            if _recurse:
                return (
                    f"**NO LANGUAGE STRING FOR {text_name} in {data}**\n"
                    "__Please forward this to @userbotindo__"
                )
            text = f"NO LANGUAGE STRING FOR {text_name} in {data}"
            self.bot.log.warning(text)
            if data == "en":
                return text
        except (IndexError, KeyError):
            text = f"Failed to format {text_name} string on {data}\n"
            self.bot.log.error(text)
            raise

        # If we're here it means that there is no string data for the text_name
        # Try to send fallback string in english
        if data != "en":
            return run_coroutine_threadsafe(
                self.text(chat_id, text_name, *args, noformat, _recurse=True, **kwargs),
                self.bot.loop,
            ).result()

    @classmethod
    def format_desc(cls, comment: Optional[str] = None):
        _comment = comment + " " if comment else ""
        return f"{_comment}plugin '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"

    def __repr__(self):
        return "<" + self.format_desc(self.comment) + ">"
