"""Anjani misc utils"""
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

from typing import TYPE_CHECKING, Any, Callable, Set, Tuple, Union

from pyrogram.filters import AndFilter, Filter, InvertFilter, OrFilter

from anjani.util.types import CustomFilter

if TYPE_CHECKING:
    from anjani.core import Anjani


def check_filters(filters: Union[Filter, CustomFilter], anjani: "Anjani") -> None:
    """Recursively check filters to set :obj:`~Anjani` into :obj:`~CustomFilter` if needed"""
    if isinstance(filters, (AndFilter, OrFilter, InvertFilter)):
        check_filters(filters.base, anjani)
    if isinstance(filters, (AndFilter, OrFilter)):
        check_filters(filters.other, anjani)

    # Only accepts CustomFilter instance
    if getattr(filters, "include_bot", False) and isinstance(filters, CustomFilter):
        filters.anjani = anjani


def find_prefixed_funcs(obj: Any, prefix: str) -> Set[Tuple[str, Callable[..., Any]]]:
    """Finds functions with symbol names matching the prefix on the given object."""

    results: Set[Tuple[str, Callable[..., Any]]] = set()

    for sym in dir(obj):
        if sym.startswith(prefix):
            name = sym[len(prefix) :]
            func = getattr(obj, sym)
            if not callable(func):
                continue

            results.add((name, func))

    return results


def do_nothing(*args: Any, **kwargs: Any) -> None:
    """Do nothing function"""
    return None


class StopPropagation(Exception):
    """Exception that raised to stop propagating an event"""
