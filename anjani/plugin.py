import codecs
import inspect
import logging
import os.path
from functools import wraps
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Protocol

from anjani import util

if TYPE_CHECKING:
    from .core import Anjani


class Func(Protocol):
    def __call__(_self,
                 self: "Plugin",
                 chat_id: int,
                 text_name: str,
                 *args: Any,
                 **kwargs: Any) -> str: ...


def loop_safe(func: Func):  # Let default typing choose the return type
    """ Decorator for text methods """

    @wraps(func)
    async def wrapper(self: "Plugin",
                      chat_id: int,
                      text_name: str,
                      *args: Any,
                      **kwargs: Any) -> str:
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
    def text(self, chat_id: int, text_name: str, *args: Any, **kwargs: Any) -> str:
        data = self.bot.chats_languages.get(chat_id, "en")
        noformat = bool(kwargs.get("noformat", False))

        try:
            text = codecs.decode(
                codecs.encode(
                    self.bot.languages[data][text_name], "latin-1", "backslashreplace"
                ),
                "unicode-escape",
            )
            return text if noformat else text.format(*args, **kwargs)
        except KeyError:
            self.bot.log.warning(f"NO LANGUAGE STRING FOR {text_name} in {data}")

        # Try to send language text in en
        try:
            text = codecs.decode(
                codecs.encode(
                    self.bot.languages["en"][text_name], "latin-1", "backslashreplace"
                ),
                "unicode-escape",
            )
            return text if noformat else text.format(*args, **kwargs)
        except KeyError:
            return (
                f"**NO LANGUAGE STRING FOR {text_name} in {data}**\n"
                "__Please forward this to @userbotindo__"
            )

    @classmethod
    def format_desc(cls, comment: Optional[str] = None):
        _comment = comment + " " if comment else ""
        return f"{_comment}plugin '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"

    def __repr__(self):
        return "<" + self.format_desc(self.comment) + ">"
