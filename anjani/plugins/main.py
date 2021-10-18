""" Main Anjani plugins """
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

import re
from typing import TYPE_CHECKING, ClassVar, List, Optional

import bson
from aiopath import AsyncPath
from pyrogram.errors import MessageDeleteForbidden, MessageNotModified
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from anjani import command, filters, listener, plugin, util

if TYPE_CHECKING:
    from .rules import Rules


class Main(plugin.Plugin):
    """Bot main Commands"""

    name: ClassVar[str] = "Main"

    bot_name: str
    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("SESSION")

    async def on_start(self, _: int) -> None:
        self.bot_name = (
            self.bot.user.first_name + self.bot.user.last_name
            if self.bot.user.last_name
            else self.bot.user.first_name
        )

    async def on_stop(self) -> None:
        file = AsyncPath("anjani/anjani.session")
        if not await file.exists():
            return

        await self.db.update_one(
            {"_id": 2}, {"$set": {"session": bson.Binary(await file.read_bytes())}}, upsert=True
        )

    async def help_builder(self, chat_id: int) -> List[List[InlineKeyboardButton]]:
        """Build the help button"""
        plugins: List[InlineKeyboardButton] = []
        for plug in list(self.bot.plugins.values()):
            if plug.helpable:
                plugins.append(
                    InlineKeyboardButton(
                        await self.text(chat_id, f"{plug.name.lower()}-button"),
                        callback_data=f"help_plugin({plug.name.lower()})",
                    )
                )

        pairs = [plugins[i * 3 : (i + 1) * 3] for i in range((len(plugins) + 3 - 1) // 3)]
        pairs.append([InlineKeyboardButton("✗ Close", callback_data="help_close")])

        return pairs

    @listener.filters(filters.regex(r"help_(.*)"))
    async def on_callback_query(self, query: CallbackQuery) -> None:
        """Bot helper button"""
        match = query.matches[0].group(1)
        chat = query.message.chat

        if match == "back":
            keyboard = await self.help_builder(chat.id)
            try:
                await query.edit_message_text(
                    await self.text(chat.id, "help-pm", self.bot_name),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="markdown",
                )
            except MessageNotModified:
                pass
        elif match == "close":
            try:
                await query.message.delete()
            except MessageDeleteForbidden:
                await query.answer("I can't delete the message")
        elif match:
            plug = re.compile(r"plugin\((\w+)\)").match(match)
            if not plug:
                raise ValueError("Unable to find plugin name")

            text_lang = await self.text(
                chat.id, f"{plug.group(1)}-help", username=self.bot.user.username
            )
            text = (
                f"Here is the help for the **{plug.group(1).capitalize()}** "
                f"plugin:\n\n{text_lang}"
            )
            if "SpamPredict" in self.bot.plugins and plug.group(1) == "spamshield":
                text += await self.text(chat.id, "spamprediction-help")
            try:
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    await self.text(chat.id, "back-button"),
                                    callback_data="help_back",
                                )
                            ]
                        ]
                    ),
                    parse_mode="markdown",
                )
            except MessageNotModified:
                pass

    async def cmd_start(self, ctx: command.Context) -> Optional[str]:
        """Bot start command"""
        chat = ctx.msg.chat

        if chat.type == "private":  # only send in PM's
            if ctx.input and ctx.input == "help":
                keyboard = await self.help_builder(chat.id)
                await ctx.respond(
                    await self.text(chat.id, "help-pm", self.bot_name),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                return None

            if ctx.input:
                rules_re = re.compile(r"rules_(.*)")
                if rules_re.search(ctx.input):
                    plug: "Rules" = self.bot.plugins["Rules"]  # type: ignore
                    return await plug.start_rules(ctx)

            buttons = [
                [
                    InlineKeyboardButton(
                        text=await self.text(chat.id, "add-to-group-button"),
                        url=f"t.me/{self.bot.user.username}?startgroup=true",
                    ),
                    InlineKeyboardButton(
                        text=await self.text(chat.id, "start-help-button"),
                        url=f"t.me/{self.bot.user.username}?start=help",
                    ),
                ]
            ]
            await ctx.respond(
                await self.text(chat.id, "start-pm", self.bot_name),
                reply_markup=InlineKeyboardMarkup(buttons),
                disable_web_page_preview=True,
                parse_mode="markdown",
            )
            return None

        return await self.text(chat.id, "start-chat")

    async def cmd_help(self, ctx: command.Context) -> None:
        """Bot plugins helper"""
        chat = ctx.msg.chat

        if chat.type != "private":  # only send in PM's
            await ctx.respond(
                await self.text(chat.id, "help-chat"),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=await self.text(chat.id, "help-chat-button"),
                                url=f"t.me/{self.bot.user.username}?start=help",
                            )
                        ]
                    ]
                ),
            )
            return

        keyboard = await self.help_builder(chat.id)
        await ctx.respond(
            await self.text(chat.id, "help-pm", self.bot_name),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def cmd_markdownhelp(self, ctx: command.Context) -> None:
        """Send markdown helper."""
        await ctx.respond(
            await self.text(ctx.chat.id, "markdown-helper", self.bot_name),
            parse_mode="html",
            disable_web_page_preview=True,
        )
