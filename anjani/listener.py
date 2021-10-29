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
        listenerFilter: Optional[Filter] = None
    ) -> None:
        self.event = event
        self.func = func
        self.plugin = plugin
        self.priority = prio
        self.filters = listenerFilter

    def __lt__(self, other: "Listener") -> bool:
        return self.priority < other.priority

    def __repr__(self) -> str:
        return f"<listener plugin '{self.event}' from '{self.plugin.name}'>"
