import codecs
import inspect
import logging
import os.path
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Optional

from anjani import util

if TYPE_CHECKING:
    from .core import Anjani


def loop_safe(func: Callable[..., Any]) -> Callable[..., Any]:

    @wraps(func)
    async def wrapper(self, *args: Any, **kwargs: Any) -> Any:
        return await util.run_sync(func, self, *args, **kwargs)

    return wrapper


class Plugin:
    # Class variables
    name: ClassVar[str] = "Unnamed"
    disabled: ClassVar[bool] = False
    helpable: ClassVar[bool] = True

    # Instance variables
    bot: "Anjani"
    log: logging.Logger
    comment: Optional[str]

    def __init__(self, bot: "Anjani") -> None:
        self.bot = bot
        self.log = logging.getLogger(type(self).name.lower().replace(" ", "_"))
        self.comment = None

    async def change_language(self, chat_id: int, lang: str) -> None:
        db = self.bot.db.get_collection("LANGUAGE")
        await db.update_one({"chat_id": chat_id}, {"$set": {"language": lang}}, upsert=True)

    @loop_safe
    def text(self, chat_id: int, text_name: str, *args: Any, **kwargs: Any) -> str:
        language = self.bot.languages.get(chat_id, "en")
        noformat = bool(kwargs.get("noformat", False))

        try:
            text = codecs.decode(
                codecs.encode(
                    self.bot.languages_data[language][text_name], "latin-1", "backslashreplace"
                ),
                "unicode-escape",
            )
            return text if noformat else text.format(*args, **kwargs)
        except KeyError:
            self.bot.log.warning(f"NO LANGUAGE STRING FOR {text_name} in {language}")

        # Try to send language text in en
        try:
            text = codecs.decode(
                codecs.encode(
                    self.bot.languages_data["en"][text_name], "latin-1", "backslashreplace"
                ),
                "unicode-escape",
            )
            return text if noformat else text.format(*args, **kwargs)
        except KeyError:
            return (
                f"**NO LANGUAGE STRING FOR {text_name} in {language}**\n"
                "__Please forward this to @userbotindo__"
            )

    @classmethod
    def format_desc(cls, comment: Optional[str] = None):
        _comment = comment + " " if comment else ""
        return f"{_comment}plugin '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"

    def __repr__(self):
        return "<" + self.format_desc(self.comment) + ">"
