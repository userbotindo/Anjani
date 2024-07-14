""" Health Check plugin for @dAnjani_bot """

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
from datetime import datetime
from typing import ClassVar

from pyrogram.raw.functions.ping import Ping


from anjani import plugin


class Health(plugin.Plugin):
    name: ClassVar[str] = "HealthCheck"
    webhook_url: str
    interval: int

    # Private
    _run_check: bool = False
    __task: asyncio.Task[None]

    async def on_load(self) -> None:
        self.webhook_url = self.bot.config.HEALTH_CHECK_WEBHOOK_URL
        if not self.webhook_url:
            self.log.debug("Health Check Webhook URL is not set, disabling health check")
            self.bot.unload_plugin(self)
            return
        self._run_check = True
        self.interval = self.bot.config.HEALTH_CHECK_INTERVAL

    async def on_start(self, _: int) -> None:
        self.log.debug("Starting Health Check Push")
        self.__task = self.bot.loop.create_task(self.push_health())

    async def on_stop(self) -> None:
        self.log.debug("Stopping health check push")
        self._run_check = False
        self.__task.cancel()

    async def push_health(self) -> None:
        while self._run_check:
            try:
                await self.bot.http.get(
                    self.webhook_url,
                    params={"status": "up", "msg": "OK", "ping": await self.get_ping()},
                )
            except Exception as e:
                self.log.error(f"Error pushing health: {e}")

            await asyncio.sleep(self.interval)

    async def get_ping(self) -> float:
        time = datetime.now()
        await self.bot.client.invoke(Ping(ping_id=1))
        end = datetime.now()
        return (end - time).microseconds / 1000
