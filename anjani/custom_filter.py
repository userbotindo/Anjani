from typing import TYPE_CHECKING, Any, Callable, Coroutine

import pyrogram
from pyrogram.filters import Filter
from pyrogram.types import Message

if TYPE_CHECKING:
    from .core import Anjani


FilterFunc = Callable[[Filter, pyrogram.Client, Message],
                      Coroutine[Any, Any, bool]]


class CustomFilter(Filter):
    anjani: "Anjani"
    include_bot: bool


def create(func: Callable, name: str = None, **kwargs) -> CustomFilter:
    return type(
        name or func.__name__ or "CustomAnjaniFilter",
        (CustomFilter,),
        {"__call__": func, **kwargs}
    )()


def _staff_only(include_bot: bool = False) -> CustomFilter:

    async def func(flt: CustomFilter, _: pyrogram.Client, message: Message) -> bool:
        user = message.from_user
        return bool(user.id in flt.anjani.staff)

    return create(func, "CustomStaffFilter", include_bot=include_bot)

staff_only = _staff_only(include_bot=True)
