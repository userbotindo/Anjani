from typing import TYPE_CHECKING

from pyrogram.filters import Filter

if TYPE_CHECKING:
    from anjani.core import Anjani


class CustomFilter(Filter):
    anjani: "Anjani"
    include_bot: bool