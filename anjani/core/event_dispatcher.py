"""Anjani event dispatcher"""
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

import asyncio
import bisect
from hashlib import sha256
from typing import TYPE_CHECKING, Any, MutableMapping, MutableSequence, Optional, Tuple

from pyrogram import raw
from pyrogram.filters import Filter
from pyrogram.raw import functions
from pyrogram.types import CallbackQuery, InlineQuery, Message

from anjani import plugin, util
from anjani.error import EventDispatchError
from anjani.listener import Listener, ListenerFunc
from anjani.util.misc import StopPropagation

from .anjani_mixin_base import MixinBase

if TYPE_CHECKING:
    from .anjani_bot import Anjani

EventType = (
    CallbackQuery,
    InlineQuery,
    Message,
)


def _get_event_data(event: Any) -> MutableMapping[str, Any]:
    if isinstance(event, Message):
        return {
            "chat_title": event.chat.title,
            "chat_id": event.chat.id,
            "user_name": event.from_user.first_name if event.from_user else event.sender_chat.title,
            "user_id": event.from_user.id if event.from_user else event.sender_chat.id,
            "input": event.text,
        }
    if isinstance(event, CallbackQuery):
        return {
            "chat_title": event.message.chat.title,
            "chat_id": event.message.chat.id,
            "user_name": event.from_user.first_name,
            "user_id": event.from_user.id,
            "input": event.data,
        }
    if isinstance(event, InlineQuery):
        return {
            "user_name": event.from_user.first_name,
            "user_id": event.from_user.id,
            "input": event.query,
        }
    return {}


def _unpack_args(args: Tuple[Any, ...]) -> str:
    """Unpack arguments into a string for logging purposes."""
    return ", ".join([str(arg) for arg in args])


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
        filters: Optional[Filter] = None,
    ) -> None:
        if event in {"load", "start", "started", "stop", "stopped"} and filters is not None:
            self.log.warning("Built-in Listener can't be use with filters. Removing...")
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
        **kwargs: Any,
    ) -> Optional[Tuple[Any, ...]]:
        results = []

        try:
            listeners = self.listeners[event]
        except KeyError:
            return None

        if not listeners:
            return None

        self.log.debug("Dispatching event '%s' with data %s", event, args)

        match = None
        index = None
        is_tg_event = False
        for lst in listeners:
            if lst.filters:
                for idx, arg in enumerate(args):
                    is_tg_event = isinstance(arg, EventType)
                    if is_tg_event:
                        if not await lst.filters(self.client, arg):
                            continue

                        match = arg.matches
                        index = idx
                        break

                    self.log.error(f"'{type(arg)}' can't be used with filters.")
                else:
                    continue

            if match and index is not None:
                args[index].matches = match

            result = None
            try:
                result = await lst.func(*args, **kwargs)
            except KeyError:
                continue
            except StopPropagation:
                break
            except Exception as err:  # skipcq: PYL-W0703
                dispatcher_error = EventDispatchError(
                    f"raised from {type(err).__name__}: {str(err)}"
                ).with_traceback(err.__traceback__)
                if is_tg_event and args[0] is not None:
                    data = _get_event_data(args[0])
                    self.log.error(
                        "Error dispatching event '%s' on %s\n"
                        "  Data:\n"
                        "    • Chat    -> %s (%d)\n"
                        "    • Invoker -> %s (%d)\n"
                        "    • Input   -> %s",
                        event,
                        lst.func.__qualname__,
                        data.get("chat_title", "Unknown"),
                        data.get("chat_id", -1),
                        data.get("user_name", "Unknown"),
                        data.get("user_id", -1),
                        data.get("input"),
                        exc_info=dispatcher_error,
                    )
                else:
                    self.log.error(
                        "Error dispatching event '%s' on %s with data\n%s",
                        event,
                        lst.func.__qualname__,
                        _unpack_args(args),
                        exc_info=dispatcher_error,
                    )
                continue
            finally:
                if result:
                    results.append(result)

                match = None
                index = None
                result = None

        return tuple(results)

    async def dispatch_missed_events(self: "Anjani") -> None:
        if not self.loaded or self._TelegramBot__running:
            return

        api_id = sha256(self.config["api_id"].encode()).hexdigest()
        collection = self.db.get_collection("SESSION")

        data = await collection.find_one({"_id": api_id})
        if not data:
            return

        pts, date = data.get("pts"), data.get("date")
        if not pts or not date:
            return

        async def send_missed_message(
            messages: list[raw.base.message.Message],
            users: MutableMapping[int, Any],
            chats: MutableMapping[int, Any],
        ) -> None:
            for message in messages:
                self.log.debug("Sending missed message with data '%s'", message)
                await self.client.dispatcher.updates_queue.put(
                    (
                        raw.types.update_new_message.UpdateNewMessage(
                            message=message, pts=0, pts_count=0
                        ),
                        users,
                        chats,
                    )
                )

        async def send_missed_update(
            updates: list[raw.base.update.Update],
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
                diff = await self.client.invoke(
                    functions.updates.get_difference.GetDifference(pts=pts, date=date, qts=-1)
                )
                if isinstance(
                    diff,
                    (
                        raw.types.updates.difference.Difference,
                        raw.types.updates.difference_slice.DifferenceSlice,
                    ),
                ):
                    if isinstance(diff, raw.types.updates.difference.Difference):
                        state: Any = diff.state
                    else:
                        state: Any = diff.intermediate_state

                    pts, date = state.pts, state.date
                    users = {u.id: u for u in diff.users}  # type: ignore
                    chats = {c.id: c for c in diff.chats}  # type: ignore

                    await asyncio.wait(
                        (
                            self.loop.create_task(
                                send_missed_message(diff.new_messages, users, chats)
                            ),
                            self.loop.create_task(
                                send_missed_update(diff.other_updates, users, chats)
                            ),
                        )
                    )
                elif isinstance(diff, raw.types.updates.difference_empty.DifferenceEmpty):
                    self.log.info("Missed event exhausted, you are up to date.")
                    date = diff.date
                    break
                elif isinstance(diff, raw.types.updates.difference_too_long.DifferenceTooLong):
                    pts = diff.pts
                    continue
                else:
                    break
        except (OSError, asyncio.CancelledError):
            pass
        finally:
            # Unset after we finished to avoid sending the same pts and date,
            # If GetState() doesn't executed on stop event
            await collection.update_one(
                {"_id": api_id},
                {"$unset": {"pts": "", "date": "", "qts": "", "seq": ""}},
            )

    async def log_stat(self: "Anjani", stat: str, *, value: int = 1) -> None:
        await self.dispatch_event("stat_listen", stat, value)
