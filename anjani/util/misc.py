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
            name = sym[len(prefix):]
            func = getattr(obj, sym)
            if not callable(func):
                continue

            results.add((name, func))

    return results
