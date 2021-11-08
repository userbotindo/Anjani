"""Anjani event dispatcher"""
# Copyright (C) 2020 - 2021  UserbotIndo Team, <https://github.com/userbotindo.git>
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

import asyncio
import bisect
from hashlib import sha256
from typing import TYPE_CHECKING, Any, MutableMapping, MutableSequence, Optional, Set

from pyrogram import raw
from pyrogram.filters import Filter
from pyrogram.raw import functions
from pyrogram.types import CallbackQuery, InlineQuery, Message

from anjani import plugin, util
from anjani.listener import Listener, ListenerFunc

from .anjani_mixin_base import MixinBase

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
        filters: Optional[Filter] = None,
    ) -> None:
        if event in {"load", "start", "started", "stop", "stopped"} and filters is not None:
            self.log.warning(f"Built-in Listener can't be use with filters. Removing...")
            filters = None

        if getattr(func, "_cmd_filters", None):
            self.log.warning(
                "@command.filters decorator only for CommandFunc. Filters will be ignored..."
            )

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
                    plug,
                    event,
                    func,
                    priority=getattr(func, "_listener_priority", 100),
                    filters=getattr(func, "_listener_filters", None),
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
        **kwargs: Any,
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

        collection = self.db.get_collection("SESSION")
        data = await collection.find_one(
            {"_id": sha256(self.config["api_id"].encode()).hexdigest()}
        )
        if not data:
            return

        pts, date = data.get("pts"), data.get("date")
        if not pts or not date:
            return

        async def send_missed_message(
            messages: list[raw.base.Message],
            users: MutableMapping[int, Any],
            chats: MutableMapping[int, Any],
        ) -> None:
            for message in messages:
                self.log.debug("Sending missed message with data '%s'", message)
                await self.client.dispatcher.updates_queue.put(
                    (
                        raw.types.UpdateNewMessage(message=message, pts=0, pts_count=0),
                        users,
                        chats,
                    )
                )

        async def send_missed_update(
            updates: list[raw.base.Update],
            users: MutableMapping[int, Any],
            chats: MutableMapping[int, Any],
        ) -> None:
            for update in updates:
                self.log.debug("Sending missed update with data '%s'", update)
                await self.client.dispatcher.updates_queue.put((update, users, chats))

        try:
            while True:
                # TO-DO
                # 1. Change qts to 0, because we want to get all missed events
                #    so we have a proper loop going on until DifferenceEmpty
                # 2. __state proper handling
                diff = await self.client.send(
                    functions.updates.GetDifference(pts=pts, date=date, qts=-1)
                )
                if isinstance(
                    diff, (raw.types.updates.Difference, raw.types.updates.DifferenceSlice)
                ):
                    if isinstance(diff, raw.types.updates.Difference):
                        state: Any = diff.state
                    else:
                        state: Any = diff.intermediate_state

                    pts, date = state.pts, state.date
                    users = {u.id: u for u in diff.users}
                    chats = {c.id: c for c in diff.chats}

                    await asyncio.wait(
                        (
                            send_missed_message(diff.new_messages, users, chats),
                            send_missed_update(diff.other_updates, users, chats),
                        )
                    )
                else:
                    if isinstance(diff, raw.types.updates.DifferenceEmpty):
                        self.log.info("Missed events exhausted, you are up to date.")
                        date = diff.date
                        break
                    elif isinstance(diff, raw.types.updates.DifferenceTooLong):
                        pts = diff.pts
                        self.log.debug(pts)
                        continue

                    break
        except (ConnectionError, OSError, asyncio.CancelledError):
            pass
        finally:
            self.__state = (pts, date)
            # Unset after we finished to avoid sending the same pts and date,
            # If GetState() doesn't executed on stop event
            await collection.update_one(
                {"_id": sha256(self.config["api_id"].encode()).hexdigest()},
                {"$unset": {"pts": "", "date": "", "qts": "", "seq": ""}},
            )

    async def log_stat(self: "Anjani", stat: str, *, value: int = 1) -> None:
        await self.dispatch_event("stat_listen", stat, value, wait=False)
