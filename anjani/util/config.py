"""Anjani config"""
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

from typing import Any, Iterator, MutableMapping, Optional, TypeVar

_KT = TypeVar("_KT", bound=str, contravariant=True)
_VT = TypeVar("_VT", covariant=True)


class TelegramConfig(MutableMapping[_KT, _VT]):
    def __init__(self, config: MutableMapping[str, Any]) -> None:
        for key, value in config.items():
            if not value:
                continue

            super().__setattr__(key, value)

    def is_plugin_disabled(self, name: str) -> bool:
        return name in self.__getattribute__("plugin_flag")

    def __contains__(self, k: _KT) -> bool:
        return k in self.__dict__

    def __delattr__(self, obj: object) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Can't delete configuration while running the bot.")

    def __delitem__(self, k: _KT) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Can't delete configuration while running the bot.")

    def __getattr__(self, name: str) -> _VT:
        return self.__getattribute__(name)

    def __getitem__(self, k: _KT) -> _VT:
        return self.__dict__[k]

    def __iter__(self) -> Iterator[str]:
        return self.__dict__.__iter__()

    def __len__(self) -> int:
        return len(self.__dict__)

    def __setattr__(self, name: str, value: Any) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Configuration must be done before running the bot.")

    def __setitem__(self, k: str, v: Any) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Configuration must be done before running the bot.")
