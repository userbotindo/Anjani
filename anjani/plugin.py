import inspect
import logging
import os.path
from typing import TYPE_CHECKING, Any, ClassVar, Coroutine, Optional

from typing_extensions import final

from anjani import util

if TYPE_CHECKING:
    from .core import Anjani


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

    # {
    # get_text and text can be declare as ClassVar but we don't do it
    # because we want to keep the documentation of the methods.

    @final
    def get_text(
        self, chat_id: int, text_name: str, *args: Any, noformat: bool = False, **kwargs: Any
    ) -> Coroutine[Any, Any, str]:
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
        return util.tg.get_text(self.bot, chat_id, text_name, *args, noformat=noformat, **kwargs)

    # Convenient alias get_text method
    @final
    def text(
        self, chat_id: int, text_name: str, *args: Any, noformat: bool = False, **kwargs: Any
    ) -> Coroutine[Any, Any, str]:
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
        return util.tg.get_text(self.bot, chat_id, text_name, *args, noformat=noformat, **kwargs)

    # }

    @classmethod
    def format_desc(cls, comment: Optional[str] = None):
        _comment = comment + " " if comment else ""
        return f"{_comment}plugin '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"

    def __repr__(self):
        return "<" + self.format_desc(self.comment) + ">"
