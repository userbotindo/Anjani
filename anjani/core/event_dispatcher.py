import asyncio
import bisect
from typing import TYPE_CHECKING, Any, MutableMapping, MutableSequence, Optional, Set

from pyrogram.filters import Filter
from pyrogram.types import (
    CallbackQuery,
    InlineQuery,
    Message,
)

from .anjani_mixin_base import MixinBase
from anjani import plugin, util
from anjani.listener import Listener, ListenerFunc

if TYPE_CHECKING:
    from .anjani_bot import Anjani

EventType = (
    CallbackQuery,
    InlineQuery,
    Message,
)


class EventDispatcher(MixinBase):
    # Initialized during instantiation
    listeners: MutableMapping[str, MutableSequence[Listener]]

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        # Initialize listener map
        self.listeners = {}

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    def register_listener(
        self: "Anjani",
        plug: plugin.Plugin,
        event: str,
        func: ListenerFunc,
        *,
        priority: int = 100,
        filters: Optional[Filter] = None
    ) -> None:
        if event in {"load", "start", "started", "stop", "stopped"} and filters is not None:
            self.log.warning(f"Built-in Listener can't be use with filters. Removing...")
            filters = None

        if getattr(func, "_cmd_filters", None):
            self.log.warning("@command.filters decorator only for CommandFunc. Filters will be ignored...")

        if filters:
            self.log.debug("Registering filter '%s' into '%s'", type(filters).__name__, event)

        listener = Listener(event, func, plug, priority, filters)

        if event in self.listeners:
            bisect.insort(self.listeners[event], listener)
        else:
            self.listeners[event] = [listener]

        self.update_plugin_events()

    def unregister_listener(self: "Anjani", listener: Listener) -> None:
        self.listeners[listener.event].remove(listener)
        # Remove list if empty
        if not self.listeners[listener.event]:
            del self.listeners[listener.event]

        self.update_plugin_events()

    def register_listeners(self: "Anjani", plug: plugin.Plugin) -> None:
        for event, func in util.misc.find_prefixed_funcs(plug, "on_"):
            done = True
            try:
                self.register_listener(
                    plug, event, func,
                    priority=getattr(func, "_listener_priority", 100),
                    filters=getattr(func, "_listener_filters", None)
                )
                done = True
            finally:
                if not done:
                    self.unregister_listeners(plug)

    def unregister_listeners(self: "Anjani", plug: plugin.Plugin) -> None:
        for lst in list(self.listeners.values()):
            for listener in lst:
                if listener.plugin == plug:
                    self.unregister_listener(listener)

    async def dispatch_event(
        self: "Anjani",
        event: str,
        *args: Any,
        wait: bool = True,
        get_tasks: bool = False,
        **kwargs: Any
    ) -> Optional[Set[asyncio.Task[Any]]]:
        tasks = set()

        try:
            listeners = self.listeners[event]
        except KeyError:
            return None

        if not listeners:
            return None

        match = None
        index = None
        for lst in listeners:
            if lst.filters:
                for idx, arg in enumerate(args):
                    if isinstance(arg, EventType):
                        permitted: bool = await lst.filters(self.client, arg)
                        if not permitted:
                            continue

                        match = arg.matches
                        index = idx
                        break

                    self.log.error(f"'{type(arg)}' can't be used with filters.")
                else:
                    continue

            task = self.loop.create_task(lst.func(*args, **kwargs))
            tasks.add(task)

        if not tasks:
            return None

        if match and index is not None:
            args[index].matches = match

        self.log.debug("Dispatching event '%s' with data %s", event, args)
        if wait:
            await asyncio.wait(tasks)

        if get_tasks:
            return tasks
        return None
