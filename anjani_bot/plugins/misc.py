"""miscellaneous bot commands"""
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

from datetime import datetime
from typing import ClassVar

from anjani_bot import anjani, plugin


class Misc(plugin.Plugin):
    name: ClassVar[str] = "Miscs"

    @anjani.on_command("ping")
    async def ping(self, message):
        """ Get bot latency """
        start = datetime.now()
        msg = await message.reply_text('`Pong!`')
        end = datetime.now()
        latency = (end - start).microseconds / 1000
        await msg.edit(f"**Pong!**\n`{latency} ms`")
