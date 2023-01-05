"""Anjani event listener"""
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

from typing import Any, Callable, Optional, Union

from pyrogram.filters import Filter

ListenerFunc = Callable[..., Any]
Decorator = Callable[[ListenerFunc], ListenerFunc]


def priority(_prio: int) -> Decorator:
    """Sets priority on the given listener function."""

    def prio_decorator(func: ListenerFunc) -> ListenerFunc:
        setattr(func, "_listener_priority", _prio)
        return func

    return prio_decorator


def filters(_filters: Filter) -> Decorator:
    """Sets filters on the given listener function."""

    def filters_decorator(func: ListenerFunc) -> ListenerFunc:
        setattr(func, "_listener_filters", _filters)
        return func

    return filters_decorator


class Listener:
    event: str
    func: Union[ListenerFunc, ListenerFunc]
    plugin: Any
    priority: int
    filters: Optional[Filter]

    def __init__(
        self,
        event: str,
        func: ListenerFunc,
        plugin: Any,
        prio: int,
        listener_filter: Optional[Filter] = None,
    ) -> None:
        self.event = event
        self.func = func
        self.plugin = plugin
        self.priority = prio
        self.filters = listener_filter

    def __lt__(self, other: "Listener") -> bool:
        return self.priority < other.priority

    def __repr__(self) -> str:
        return f"<listener plugin '{self.event}' from '{self.plugin.name}'>"
