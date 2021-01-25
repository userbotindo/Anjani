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

import os
from datetime import datetime
from typing import ClassVar

from anjani_bot import anjani, plugin
from anjani_bot.config import Config
from anjani_bot.utils import nekobin


class Misc(plugin.Plugin):
    name: ClassVar[str] = "Miscs"

    @anjani.on_command("paste")
    async def paste(self, message):
        """ Paste a text to Nekobin """
        reply = message.reply_to_message
        if not reply:
            return
        sent = await message.reply_text(
            await self.text(message.chat.id, "wait-paste")
        )
        if reply and reply.document:
            file = await reply.download(Config.DOWNLOAD_PATH)
            with open(file, 'r') as text:
                data = text.read()
            os.remove(file)
        elif reply and reply.text:
            data = reply.text
        else:
            return
        key = await nekobin(self, data)
        if key:
            msg = f"**Pasted to Nekobin**\n[URL](https://nekobin.com/{key})"
            await sent.edit_text(msg, disable_web_page_preview=True)
        else:
            await sent.edit_text(
                await self.text(message.chat.id, "fail-paste")
            )

    @anjani.on_command("ping")
    async def ping(self, message):
        """ Get bot latency """
        start = datetime.now()
        msg = await message.reply_text('`Pong!`')
        end = datetime.now()
        latency = (end - start).microseconds / 1000
        await msg.edit(f"**Pong!**\n`{latency} ms`")
