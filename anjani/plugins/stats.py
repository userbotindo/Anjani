"""Bot stats plugin"""
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
from typing import Any, ClassVar, Optional

from pyrogram.types import Message

from anjani import command, filters, plugin, util

USEC_PER_HOUR = 60 * 60 * 1000000
USEC_PER_DAY = USEC_PER_HOUR * 24


def _calc_pct(num1: int, num2: int) -> str:
    if not num2:
        return "0"

    return "{:.1f}".format((num1 / num2) * 100).rstrip("0").rstrip(".")


def _calc_ph(stat: int, uptime: int) -> str:
    up_hr = max(1, uptime) / USEC_PER_HOUR
    return "{:.1f}".format(stat / up_hr).rstrip("0").rstrip(".")


def _calc_pd(stat: int, uptime: int) -> str:
    up_day = max(1, uptime) / USEC_PER_DAY
    return "{:.1f}".format(stat / up_day).rstrip("0").rstrip(".")


class PluginStats(plugin.Plugin):
    name: ClassVar[str] = "Stats"

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("STATS")

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
        await self.db.find_one_and_update({"_id": 1}, {"$inc": {key: value}}, upsert=True)

    async def delete(self, key: str) -> None:
        await self.db.find_one_and_update({"_id": 1}, {"$unset": {key: ""}})

    async def put(self, key: str, value: int) -> None:
        await self.db.find_one_and_update({"_id": 1}, {"$set": {key: value}}, upsert=True)

    @command.filters(filters.dev_only)
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
        )
        for index, stat in enumerate(resp):
            if stat is None:
                resp[index] = 0
        downtime, recv, processed, predicted, spam_detected, spam_deleted, banned = resp
        text = f"""<b><i>Stats since last reset</i></b>\n
<b>Total Uptime elapsed</b>: <b>{util.time.format_duration_us(uptime - downtime)}</b>
<b>Total Downtime elapsed</b>: <b>{util.time.format_duration_us(downtime)}</b>
<b>Messages received</b>: <b>{recv}</b> (<b><i>{_calc_ph(recv, uptime)}/h</i></b>)
  • <b>{predicted}</b> (<b><i>{_calc_ph(predicted, uptime)}/h</i></b>) messages predicted - <b>{_calc_pct(predicted, recv)}%</b> from received messages
  • <b>{spam_detected}</b> messages were detected as spam - <b>{_calc_pct(spam_detected, predicted)}%</b> of predicted messages
  • <b>{spam_deleted}</b> messages were deleted from spam - <b>{_calc_pct(spam_deleted, spam_detected)}%</b> of detected messages
<b>Commands processed</b>: <b>{processed}</b> (<b><i>{_calc_ph(processed, uptime)}/h</i></b>)
  • <b>{_calc_pct(processed, recv)}%</b> from received messages
<b>Auto banned users</b>: <b>{banned}</b> (<b><i>{_calc_pd(banned, uptime)}/day</i></b>)
"""
        async with ctx.action():
            await ctx.respond(text, parse_mode="html")
            return None
