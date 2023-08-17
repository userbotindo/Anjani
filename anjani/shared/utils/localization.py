import codecs
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional

from typing_extensions import ParamSpecArgs, ParamSpecKwargs

from ..types import common as _types
from ..utils import run_sync

if TYPE_CHECKING:
    from anjani.core import Anjani


def __loop_safe(
    func: Callable[
        [
            _types.Bot,
            _types.ChatId,
            _types.TextName,
            ParamSpecArgs,
            _types.NoFormat,
            ParamSpecKwargs,
        ],
        str,
    ]
):  # Special: let default typing choose the return type
    """Decorator for get_text functions"""

    @wraps(func)
    async def wrapper(
        bot: "Anjani",
        chat_id: Optional[int],
        text_name: str,
        *args: Any,
        noformat: bool = False,
        **kwargs: Any,
    ) -> str:
        """Parse the string with user locale language setting.

        Parameters:
            bot (`Anjani`):
                The bot instance.
            chat_id (`int`, *Optional*):
                Id of the sender(PM's) or chat_id to fetch the user language setting.
                If chat_id is None, the language will always use 'en'.
            text_name (`str`):
                String name to parse. The string is parsed from YAML documents.
            *args (`any`, *Optional*):
                One or more values that should be formatted and inserted in the string.
                The value should be in order based on the language string placeholder.
            noformat (`bool`, *Optional*):
                If True, the text returned will not be formated.
                Default to False.
            **kwargs (`any`, *Optional*):
                One or more keyword values that should be formatted and inserted in the string.
                based on the keyword on the language strings.
        """
        return await run_sync(func, bot, chat_id, text_name, *args, noformat=noformat, **kwargs)

    return wrapper


@__loop_safe
def get_text(
    bot: "Anjani",
    chat_id: Optional[int],
    text_name: str,
    *args: Any,
    noformat: bool = False,
    **kwargs: Any,
) -> str:
    def _get_text(lang: str) -> str:
        try:
            text = codecs.decode(
                codecs.encode(bot.languages[lang][text_name], "latin-1", "backslashreplace"),
                "unicode-escape",
            )
        except KeyError:
            if lang == "en":
                return (
                    f"**NO LANGUAGE STRING FOR '{text_name}' in '{lang}'**\n"
                    "__Please forward this to__ @userbotindo"
                )

            bot.log.warning("NO LANGUAGE STRING FOR '%s' in '%s'", text_name, lang)
            return _get_text("en")
        else:
            try:
                return text if noformat else text.format(*args, **kwargs)
            except (IndexError, KeyError):
                bot.log.error("Failed to format '%s' string on '%s'", text_name, lang)
                raise

    return _get_text(bot.chats_languages.get(chat_id or 0, "en"))
