import codecs
import inspect
import logging
import os.path
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Optional

from anjani import util

if TYPE_CHECKING:
    from .core import Anjani


def loop_safe(func: Callable[..., str]):  # Let default typing choose the return type
    """ Decorator for text methods """

    @wraps(func)
    async def wrapper(
        self: "Plugin",
        chat_id: int,
        text_name: str,
        *args: Any,
        noformat: bool = False,
        **kwargs: Any
    ) -> str:
        return await util.run_sync(
            func,
            self,
            chat_id,
            text_name,
            *args,
            noformat=noformat,
            **kwargs
        )

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
        **kwargs: Any
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
        def get_text(lang_code: str) -> str:
            try:
                text = codecs.decode(
                    codecs.encode(
                        self.bot.languages[lang_code][text_name],
                        "latin-1",
                        "backslashreplace"
                    ),
                    "unicode-escape",
                )
            except KeyError:
                if lang_code == "en":
                    return (
                        f"**NO LANGUAGE STRING FOR '{text_name}' in '{lang_code}'**\n"
                        "__Please forward this to__ @userbotindo"
                    )

                self.bot.log.warning(f"NO LANGUAGE STRING FOR '{text_name}' in '{lang_code}'")
                return get_text("en")
            else:
                try:
                    return text if noformat else text.format(*args, **kwargs)
                except (IndexError, KeyError):
                    self.bot.log.error(f"Failed to format '{text_name}'' string on '{lang_code}'")
                    raise

        data = self.bot.chats_languages.get(chat_id, "en")
        return get_text(data)

    @classmethod
    def format_desc(cls, comment: Optional[str] = None):
        _comment = comment + " " if comment else ""
        return f"{_comment}plugin '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"

    def __repr__(self):
        return "<" + self.format_desc(self.comment) + ">"
