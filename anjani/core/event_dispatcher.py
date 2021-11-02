import asyncio
import bisect
from typing import TYPE_CHECKING, Any, MutableMapping, MutableSequence, Optional, Set

from pyrogram import raw
from pyrogram.filters import Filter
from pyrogram.raw import functions
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

    # Initialized runtime
    __state: tuple[int, int]

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

    async def dispatch_missed_events(self: "Anjani") -> None:
        if not self.loaded or self._TelegramBot__running:
            return

        data = await self.db.get_collection("SESSION").find_one({"_id": 2})
        if not data:
            return

        pts, date = data.get("pts"), data.get("date")
        if not pts or not date:
            return

        try:
            while True:
                diff = await self.client.send(
                    functions.updates.GetDifference(pts=pts, date=date, qts=-1)
                )
                if isinstance(diff, (raw.types.updates.Difference, raw.types.updates.DifferenceSlice)):
                    if isinstance(diff, raw.types.updates.Difference):
                        state: Any = diff.state
                    else:
                        state: Any = diff.intermediate_state

                    pts, date = state.pts, state.date
                    users = {u.id: u for u in diff.users}  # type: ignore
                    chats = {c.id: c for c in diff.chats}  # type: ignore

                    if diff.new_messages:
                        for message in diff.new_messages:
                            self.client.dispatcher.updates_queue.put_nowait((
                                raw.types.UpdateNewMessage(message=message, pts=0, pts_count=0),
                                users, chats,
                            ))

                    if diff.other_updates:
                        for update in diff.other_updates:
                            self.client.dispatcher.updates_queue.put_nowait((update, users, chats))

                    await self.log_stat("missed_events", value=len(diff.new_messages) + len(diff.other_updates))
                else:
                    if isinstance(diff, raw.types.updates.DifferenceEmpty):
                        date = diff.date
                        self.log.debug(date)
                    elif isinstance(diff, raw.types.updates.DifferenceTooLong):
                        pts = diff.pts
                        self.log.debug(pts)
                    break
        except (ConnectionError, OSError, asyncio.CancelledError):
            pass
        finally:
            self.__state = (pts, date)

    async def log_stat(self: "Anjani", stat: str, *, value: int = 1) -> None:
        await self.dispatch_event("stat_listen", stat, value, wait=False)
