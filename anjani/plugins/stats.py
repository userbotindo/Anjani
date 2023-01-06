"""Bot stats plugin"""
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
from typing import Any, ClassVar, List, Mapping, Optional

from pyrogram.enums.parse_mode import ParseMode
from pyrogram.types import Message

from anjani import command, filters, plugin, util

USEC_PER_HOUR = 60 * 60 * 1000000
USEC_PER_DAY = USEC_PER_HOUR * 24


def _calc_pct(num1: int, num2: int) -> str:
    if not num2:
        return "0"

    return f"{(num1 / num2) * 100:.1f}".rstrip("0").rstrip(".")


def _calc_ph(stat: int, uptime: int) -> str:
    up_hr = max(1, uptime) / USEC_PER_HOUR
    return f"{stat / up_hr:.1f}".rstrip("0").rstrip(".")


def _calc_pd(stat: int, uptime: int) -> str:
    up_day = max(1, uptime) / USEC_PER_DAY
    return f"{stat / up_day:.1f}".rstrip("0").rstrip(".")


class PluginStats(plugin.Plugin):
    name: ClassVar[str] = "Stats"

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("STATS")
        self.chats_db = self.bot.db.get_collection("CHATS")
        self.users_db = self.bot.db.get_collection("USERS")
        self.feds_db = self.bot.db.get_collection("FEDERATIONS")

        if await self.get("stop_time_usec") or await self.get("uptime"):
            self.log.info("Migrating stats timekeeping format")

        last_time = await self.get("stop_time_usec")
        if last_time:
            await self.inc("uptime", util.time.usec() - last_time)
            await self.delete("stop_time_usec")

        uptime = await self.get("uptime")
        if uptime:
            await self.put("start_time_usec", self.bot.start_time_us - uptime)
            await self.delete("uptime")

    async def on_start(self, time_us: int) -> None:
        # Initialize start_time_usec for new instances
        if not await self.get("start_time_usec"):
            await self.put("start_time_usec", time_us)

    async def on_stat_listen(self, key: str, value: int) -> None:
        await self.inc(key, value)

    async def on_message(self, message: Message) -> None:
        stat = "sent" if message.outgoing else "received"
        await self.bot.log_stat(stat)

    async def on_command(
        self, ctx: command.Context, cmd: command.Command  # skipcq: PYL-W0613
    ) -> None:
        await self.bot.log_stat("processed")

    async def get(self, key: str) -> Optional[Any]:
        collection = await self.db.find_one({"_id": 1})
        return collection.get(key) if collection else None

    async def inc(self, key: str, value: int) -> None:
        await self.db.update_one({"_id": 1}, {"$inc": {key: value}}, upsert=True)

    async def delete(self, key: str) -> None:
        await self.db.update_one({"_id": 1}, {"$unset": {key: ""}})

    async def put(self, key: str, value: int) -> None:
        await self.db.update_one({"_id": 1}, {"$set": {key: value}}, upsert=True)

    @command.filters(filters.dev_only & filters.private)
    async def cmd_stats(self, ctx: command.Context) -> None:
        if ctx.input == "reset":
            await self.db.delete_many({})
            await self.on_load()
            await self.on_start(util.time.usec())
            self.bot.loop.create_task(util.tg.reply_and_delete(ctx.msg, "Stats reset", 5))
            return None

        start_time: Optional[int] = await self.get("start_time_usec")
        if start_time is None:
            start_time = util.time.usec()
            await self.put("start_time_usec", start_time)

        uptime = util.time.usec() - start_time
        resp = await asyncio.gather(
            self.get("downtime"),
            self.get("received"),
            self.get("processed"),
            self.get("predicted"),
            self.get("spam_detected"),
            self.get("spam_deleted"),
            self.get("banned"),
            self.users_db.count_documents({}),
            self.chats_db.count_documents({}),
        )
        for index, stat in enumerate(resp):
            if stat is None:
                resp[index] = 0

        (
            downtime,
            recv,
            processed,
            predicted,
            spam_detected,
            spam_deleted,
            banned,
            total_users,
            total_chats,
        ) = resp
        total_federations = 0
        total_fbanned = 0
        total_chat_fbanned = 0
        pipeline: List[Mapping[str, Any]] = [
            {
                "$project": {
                    "_id": 1,
                    "name": 1,
                    "banned_user": {"$size": {"$objectToArray": {"$ifNull": ["$banned", {}]}}},
                    "banned_chat": {"$size": {"$objectToArray": {"$ifNull": ["$banned_chat", {}]}}},
                }
            }
        ]

        async for opt in self.feds_db.aggregate(pipeline=pipeline):
            total_federations += 1
            total_fbanned += opt.get("banned_user", 0)
            total_chat_fbanned += opt.get("banned_chat", 0)

        text = f"""<b>STATS  SINCE  LAST  RESET</b>:\n
  • <b>Total Uptime Elapsed</b>: <b>{util.time.format_duration_us(uptime - downtime)}</b>
  • <b>Total Downtime Elapsed</b>: <b>{util.time.format_duration_us(downtime)}</b>
  • <b>Messages Received</b>: <b>{recv}</b> (<b><i>{_calc_ph(recv, uptime)}/h</i></b>)
     × <b>{predicted}</b> (<b><i>{_calc_ph(predicted, uptime)}/h</i></b>) messages predicted - <b>{_calc_pct(predicted, recv)}%</b> from received messages
     × <b>{spam_detected}</b> messages were detected as spam - <b>{_calc_pct(spam_detected, predicted)}%</b> of predicted messages
     × <b>{spam_deleted}</b> messages were deleted from spam - <b>{_calc_pct(spam_deleted, spam_detected)}%</b> of detected messages
  • <b>Commands Processed</b>: <b>{processed}</b> (<b><i>{_calc_ph(processed, uptime)}/h</i></b>)
     × <b>{_calc_pct(processed, recv)}%</b> from received messages
  • <b>Total Users</b>: <b>{total_users}</b>
  • <b>Total Chats</b>: <b>{total_chats}</b>
  • <b>Total Federations</b>: <b>{total_federations}</b>
     × <b>Total Fbanned Users</b>: <b>{total_fbanned}</b>
     × <b>Total Fbanned Chats</b>: <b>{total_chat_fbanned}</b>
  • <b>Auto Banned Users</b>: <b>{banned}</b> (<b><i>{_calc_pd(banned, uptime)}/day</i></b>)
"""
        async with ctx.action():
            await ctx.respond(text, parse_mode=ParseMode.HTML)
            return None
