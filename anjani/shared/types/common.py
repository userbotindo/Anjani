from typing import TYPE_CHECKING, Any, Callable, List, Protocol, Tuple, TypeVar, Union

from pyrogram.filters import Filter

if TYPE_CHECKING:
    from anjani.core import Anjani

Bot = TypeVar("Bot", bound="Anjani", covariant=True)
ChatId = TypeVar("ChatId", int, None, covariant=True)
TextName = TypeVar("TextName", bound=str, covariant=True)
NoFormat = TypeVar("NoFormat", bound=bool, covariant=True)
TypeData = TypeVar("TypeData", covariant=True)
DecoratedCallable = TypeVar("DecoratedCallable", bound=Callable[..., Any])


class Instantiable(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


class CustomFilter(Filter):
    anjani: "Anjani"
    include_bot: bool


Button = Union[Tuple[Tuple[str, str, bool]], List[Tuple[str, str, bool]]]
