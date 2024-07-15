"""Anjani custom types"""

# Copyright (C) 2020 - 2023  UserbotIndo Team, <https://github.com/userbotindo.git>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from typing import TYPE_CHECKING, Any, Callable, Protocol, TypeVar

from pyrogram.filters import Filter

if TYPE_CHECKING:
    from anjani.core import Anjani

Bot = TypeVar("Bot", bound="Anjani", covariant=True)
ChatId = TypeVar("ChatId", int, None, covariant=True)
TextName = TypeVar("TextName", bound=str, covariant=True)
NoFormat = TypeVar("NoFormat", bound=bool, covariant=True)


class CustomFilter(Filter):  # skipcq: PYL-W0223
    anjani: "Anjani"
    include_bot: bool
