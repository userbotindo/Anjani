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
        prefix = func.__name__.split("_", 1)
        if prefix[0] != "on":
            raise RuntimeError("Only Listener are able to use the listener filters.")

        try:
            if prefix[1] in {"load", "start", "started", "stop", "stopped"}:
                raise RuntimeError("Built-in Listener cannot use listener filters.")
        except IndexError:
            pass

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
        filt: Filter = None
    ) -> None:
        self.event = event
        self.func = func
        self.plugin = plugin
        self.priority = prio
        self.filters = filt

    def __lt__(self, other: "Listener") -> bool:
        return self.priority < other.priority
