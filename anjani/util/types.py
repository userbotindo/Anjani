from typing import TYPE_CHECKING, Any, Iterable, Protocol, TypeVar

from pyrogram.filters import Filter

if TYPE_CHECKING:
    from anjani.core import Anjani

TypeData = TypeVar("TypeData", covariant=True)


class CustomFilter(Filter):
    anjani: "Anjani"
    include_bot: bool


class NDArray(Protocol[TypeData]):

    def __getitem__(self, key: int) -> Any:
        ...

    @property
    def size(self) -> int:
        ...


class Pipeline(Protocol):

    def predict(self, X: Iterable[Any], **predict_params: Any) -> NDArray[Any]:
        ...

    def predict_proba(self, X: Iterable[Any]) -> NDArray[Any]:
        ...
