import codecs
import inspect
import logging
import os.path
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Type

from anjani import error

if TYPE_CHECKING:
    from .core import Anjani
    from .command import Command


class Plugin:
    # Class variables
    name: ClassVar[str] = "Unnamed"
    disabled: ClassVar[bool] = False

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
        await db.update_one(
            {"chat_id": chat_id},
            {"$set": {"language": lang}},
            upsert=True
        )

    def text(self, chat_id: int, text_name: str, *args: Any, **kwargs: Any) -> str:
        language = self.bot.languages.get(chat_id, "en")
        noformat = bool(kwargs.get("noformat", False))

        try:
            text = codecs.decode(codecs.encode(
                self.bot.languages_data[language][text_name],
                "latin-1",
                "backslashreplace"),
                "unicode-escape"
            )
            return text if noformat else text.format(*args, **kwargs)
        except KeyError:
            self.bot.log.warning(f"NO LANGUAGE STRING FOR {text_name} in {language}")

        # Try to send language text in en
        try:
            text = codecs.decode(codecs.encode(
                self.bot.languages_data["en"][text_name],
                "latin-1",
                "backslashreplace"),
                "unicode-escape"
            )
            return text if noformat else text.format(*args, **kwargs)
        except KeyError:
            return (f"**NO LANGUAGE STRING FOR {text_name} in {language}**\n"
                    "__Please forward this to @userbotindo__")

    @classmethod
    def format_desc(cls, comment: Optional[str] = None):
        _comment = comment + " " if comment else ""
        return f"{_comment}plugin '{cls.name}' ({cls.__name__}) from '{os.path.relpath(inspect.getfile(cls))}'"

    def __repr__(self):
        return "<" + self.format_desc(self.comment) + ">"


class PluginLoadError(error.AnjaniException):
    pass


class ExistingPluginError(PluginLoadError):
    old_plugin: Type[Plugin]
    new_plugin: Type[Plugin]

    def __init__(self, old_plugin: Type[Plugin], new_plugin: Type[Plugin]) -> None:
        super().__init__(
            f"Plugin '{old_plugin.name}' ({old_plugin.__name__}) already exists"
        )

        self.old_plugin = old_plugin
        self.new_plugin = new_plugin


class ExistingCommandError(PluginLoadError):
    old_cmd: "Command"
    new_cmd: "Command"
    alias: bool

    def __init__(
        self, old_cmd: "Command", new_cmd: "Command", alias: bool = False
    ) -> None:
        al_str = "alias of " if alias else ""
        old_name = type(old_cmd.plugin).__name__
        new_name = type(new_cmd.plugin).__name__
        super().__init__(
            f"Attempt to replace existing command '{old_cmd.name}' (from {old_name}) with {al_str}'{new_cmd.name}' (from {new_name})"
        )

        self.old_cmd = old_cmd
        self.new_cmd = new_cmd
        self.alias = alias