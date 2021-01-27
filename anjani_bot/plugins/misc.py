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

from covid import Covid
from pyrogram import filters

from anjani_bot import anjani, plugin
from anjani_bot.core.pool import run_in_thread
from anjani_bot.config import Config
from anjani_bot.utils import nekobin, format_integer


class Misc(plugin.Plugin):
    name: ClassVar[str] = "Miscs"

    @anjani.on_command("covid")
    async def covid(self, message):
        """ Fetch stats about Covid-19 """
        cov = await run_in_thread(Covid)(source="worldometers")

        if message.command:
            if message.command[0].lower() == "korea":
                country = "s. korea"
                link = "https://www.worldometers.info/coronavirus/country/south-korea"
            else:
                country = message.command[0]
                link = f"https://www.worldometers.info/coronavirus/country/{country}"
        else:
            country = "world"
            link = "https://www.worldometers.info/coronavirus"

        try:
            data = cov.get_status_by_country_name(country)
        except ValueError:
            return await message.reply_text(f"Invalid country {country}!")

        total_tests = "N/A"
        if data["total_tests"] != 0:
            total_tests = data["total_tests"]

        date = datetime.now().strftime("%d %b %Y")

        output = await self.text(
            message.chat.id,
            "covid-text",
            country=data['country'],
            date=date,
            confirmed=format_integer(data['confirmed']),
            active=format_integer(data['active']),
            deaths=format_integer(data['deaths']),
            recovered=format_integer(data['recovered']),
            new_cases=format_integer(data['new_cases']),
            new_deaths=format_integer(data['new_deaths']),
            critical=format_integer(data['critical']),
            total_tests=format_integer(total_tests),
            link=link,
        )

        await message.reply_text(output, disable_web_page_preview=True)

    @anjani.on_command("id")
    async def get_id(self, message):
        """ Display ID's """
        msg = message.reply_to_message or message
        out_str = f"👥 Chat ID : `{(msg.forward_from_chat or msg.chat).id}`\n"
        out_str += f"💬 Message ID : `{msg.forward_from_message_id or msg.message_id}`\n"
        out_str += f"🙋‍♂️ From User ID : `{msg.from_user.id}`\n"
        file = (
            msg.audio or msg.animation or msg.document
            or msg.photo or msg.sticker or msg.voice
            or msg.video_note or msg.video
        ) or None
        if file:
            out_str += f"📄 Media Type: `{file.__class__.__name__}`\n"
            out_str += f"📄 File ID: {file.file_id}"
        await message.reply_text(out_str)

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

    @anjani.on_command("source", filters.private)
    async def src(self, message):
        """ Send the bot source code """
        await message.reply_text(
            "[GitHub repo](https://github.com/userbotindo/Anjani)\n" +
            "[Support](https://t.me/userbotindo)",
            disable_web_page_preview=True
        )
