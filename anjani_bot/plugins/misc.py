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
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani_bot import listener, plugin
from anjani_bot.core.pool import run_in_thread
from anjani_bot.utils import dogbin, format_integer


class Misc(plugin.Plugin):
    name: ClassVar[str] = "Miscs"
    helpable: ClassVar[bool] = True

    @listener.on("ping")
    async def ping(self, message):
        """Get bot latency"""
        start = datetime.now()
        msg = await message.reply_text("`Pong!`")
        end = datetime.now()
        latency = (end - start).microseconds / 1000
        await msg.edit(f"**Pong!**\n`{latency} ms`")

    @listener.on("covid")
    async def covid(self, message):
        """Fetch stats about Covid-19"""
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

        output = await self.bot.text(
            message.chat.id,
            "covid-text",
            country=data["country"],
            date=date,
            confirmed=format_integer(data["confirmed"]),
            active=format_integer(data["active"]),
            deaths=format_integer(data["deaths"]),
            recovered=format_integer(data["recovered"]),
            new_cases=format_integer(data["new_cases"]),
            new_deaths=format_integer(data["new_deaths"]),
            critical=format_integer(data["critical"]),
            total_tests=format_integer(total_tests),
            link=link,
        )

        await message.reply_text(output, disable_web_page_preview=True)

    @listener.on(["id", "ids"])
    async def get_id(self, message):
        """Display ID's"""
        msg = message.reply_to_message or message
        out_str = f"👥 **Chat ID :** `{(msg.forward_from_chat or msg.chat).id}`\n"
        out_str += f"💬 **Message ID :** `{msg.forward_from_message_id or msg.message_id}`\n"
        if msg.from_user:
            out_str += f"🙋‍♂️ **From User ID :** `{msg.from_user.id}`\n"
        file = (
            msg.audio
            or msg.animation
            or msg.document
            or msg.photo
            or msg.sticker
            or msg.voice
            or msg.video_note
            or msg.video
        ) or None
        if file:
            out_str += f"📄 **Media Type :** `{file.__class__.__name__}`\n"
            out_str += f"📄 **File ID :** `{file.file_id}`"
        await message.reply_text(out_str)

    @listener.on("paste")
    async def paste(self, message):
        """Paste a text to Dogbin"""
        reply = message.reply_to_message
        if not reply:
            return
        sent = await message.reply_text(await self.bot.text(message.chat.id, "wait-paste"))
        if reply and reply.document:
            file = await reply.download(self.bot.get_config.download_path)
            with open(file, "r") as text:
                data = text.read()
            os.remove(file)
        elif reply and reply.text:
            data = reply.text
        else:
            return
        key = await dogbin(self.bot, data)
        if key:
            btn = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Dogbin", url=f"https://del.dog/{key}"),
                        InlineKeyboardButton(text="Dogbin Raw", url=f"https://del.dog/raw/{key}"),
                    ]
                ]
            )
            await sent.edit_text(
                await self.bot.text(message.chat.id, "paste-succes"), reply_markup=btn
            )
        else:
            await sent.edit_text(await self.bot.text(message.chat.id, "fail-paste"))

    @listener.on("source", filters.private)
    async def src(self, message):
        """Send the bot source code"""
        await message.reply_text(
            "[GitHub repo](https://github.com/userbotindo/Anjani)\n"
            + "[Support](https://t.me/userbotindo)",
            disable_web_page_preview=True,
        )

    @listener.on("slap", filters.group)
    async def neko_slap(self, message):
        """Slap member with neko slap."""
        text = " ".join(message.command)
        chat_id = message.chat.id
        async with self.bot.http.get("https://www.nekos.life/api/v2/img/slap") as slap:
            if slap.status != 200:
                return await message.reply(await self.bot.text(chat_id, "err-api-down"))
            res = await slap.json()

        reply_to = message.reply_to_message or message
        await self.bot.client.send_animation(
            message.chat.id,
            res["url"],
            reply_to_message_id=reply_to.message_id,
            caption=text,
        )
