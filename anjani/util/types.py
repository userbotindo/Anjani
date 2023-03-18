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

from abc import abstractmethod, abstractproperty
from typing import TYPE_CHECKING, Any, Iterable, Optional, Protocol, TypeVar

from aiohttp import ClientSession
from pyrogram.filters import Filter

if TYPE_CHECKING:
    from anjani.core import Anjani

Bot = TypeVar("Bot", bound="Anjani", covariant=True)
ChatId = TypeVar("ChatId", int, None, covariant=True)
TextName = TypeVar("TextName", bound=str, covariant=True)
NoFormat = TypeVar("NoFormat", bound=bool, covariant=True)
TypeData = TypeVar("TypeData", covariant=True)


class CustomFilter(Filter):  # skipcq: PYL-W0223
    anjani: "Anjani"
    include_bot: bool


class NDArray(Protocol[TypeData]):
    @abstractmethod
    def __getitem__(self, key: int) -> Any:
        raise NotImplementedError

    @abstractproperty
    def size(self) -> int:
        raise NotImplementedError


class Classifier(Protocol):
    @abstractmethod
    async def predict(self, text: str, **predict_params: Any) -> NDArray[Any]:
        raise NotImplementedError

    @abstractmethod
    async def load_model(self, http_client: ClientSession) -> None:
        raise NotImplementedError

    @abstractmethod
    async def is_spam(self, text: str) -> bool:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def normalize(text: str) -> str:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def prob_to_string(value: float) -> str:
        raise NotImplementedError
