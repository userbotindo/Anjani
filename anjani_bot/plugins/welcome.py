"""Bot Greetings"""
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
from html import escape
from typing import ClassVar, Tuple

from pyrogram import filters

from .. import anjani, plugin


class NewChatMember:
    """ A new joined user Attribute

    Attributes:
        first_name (`str`):
            User's or bot's first name.

        fullname (`str`):
            User's full name. use user first_name if not exist.

        mention (`str`):
            A text mention for this user.

        username (`str`):
            User's username.

        count (`int`, *Optional*):
            Number of members in the chat.
    """
    def __init__(self, user):
        self.first_name = user.first_name
        if user.last_name:
            self.fullname = self.first_name + user.last_name
        else:
            self.fullname = self.first_name
        self.mention = user.mention(style="html")
        if user.username:
            self.username = f"@{user.username}"
        else:
            self.username = self.mention
        self.count = None

    async def get_members(self, chat_id):
        """ Count chat member """
        self.count = await anjani.get_chat_members_count(chat_id)


class RawGreeting:
    lock = asyncio.Lock()
    welcome_db = anjani.get_collection("WELCOME")

    @staticmethod
    async def default_welc(chat_id):
        """ Bot default welcome """
        return await anjani.text(chat_id, "default-welcome", noformat=True)

    @staticmethod
    async def parse_user(user, chat_id) -> NewChatMember:
        """ Get user attribute """
        parsed_user = NewChatMember(user)
        await parsed_user.get_members(chat_id)
        return parsed_user

    @classmethod
    async def full_welcome(cls, chat_id) -> Tuple[bool, str, bool]:
        """ Get chat full welcome data """
        sett, text = await cls.welc_pref(chat_id)
        clean_serv = await cls.clean_service(chat_id)
        return sett, text, clean_serv

    @classmethod
    async def welc_pref(cls, chat_id) -> Tuple[bool, str]:
        """ Get chat welcome setting """
        setting = await cls.welcome_db.find_one({'chat_id': chat_id})
        if setting:
            return (
                setting["should_welcome"],
                setting.get("custom_welcome", await cls.default_welc(chat_id))
            )
        return True, await cls.default_welc(chat_id)

    @classmethod
    async def clean_service(cls, chat_id) -> bool:
        """ Fetch clean service setting """
        clean = await cls.welcome_db.find_one({'chat_id': chat_id})
        if clean:
            return clean.get("clean_service", False)
        return False

    @classmethod
    async def set_custom_welcome(cls, chat_id, text):
        """ Set custome welcome """
        async with cls.lock:
            await cls.welcome_db.update_one(
                {'chat_id': chat_id},
                {
                    "$set": {
                        'should_welcome': True,
                        'custom_welcome': text,
                        'clean_service': False
                    }
                },
                upsert=True
            )

    @classmethod
    async def set_cleanserv(cls, chat_id, setting):
        """ Clean service db """
        async with cls.lock:
            await cls.welcome_db.update_one(
                {'chat_id': chat_id},
                {
                    "$set": {
                        'clean_service': setting
                    }
                },
                upsert=True
            )

    @classmethod
    async def set_welc_pref(cls, chat_id, setting: bool):
        """ Turn on/off welcome in chats """
        async with cls.lock:
            await cls.welcome_db.update_one(
                {'chat_id': chat_id},
                {
                    "$set": {'should_welcome': setting}
                },
                upsert=True
            )


class Greeting(plugin.Plugin, RawGreeting):
    name: ClassVar[str] = "Greetings"
    helpable: ClassVar[bool] = True

    @anjani.on_message(filters.new_chat_members, group=3)
    async def new_member(self, message):
        """ Greet new member """
        chat = message.chat
        new_members = message.new_chat_members

        should_welc, welcome_text = await Greeting.welc_pref(chat.id)
        if should_welc:
            reply = message.message_id
            clean_serv = await Greeting.clean_service(chat.id)
            if clean_serv:
                await message.delete()
                reply = False
            for new_member in new_members:
                if new_member.id == self.id:
                    await self.send_message(
                        chat.id,
                        await self.text(chat.id, "bot-added"),
                        reply_to_message_id=reply
                    )
                else:
                    user = await Greeting.parse_user(new_member, chat.id)
                    formatted_text = welcome_text.format(
                        first=escape(user.first_name),
                        last=escape(new_member.last_name or user.first_name),
                        fullname=escape(user.fullname),
                        username=user.username,
                        mention=user.mention,
                        count=user.count,
                        chatname=escape(chat.title),
                        id=new_member.id)

                    await self.send_message(
                        chat.id,
                        formatted_text,
                        reply_to_message_id=reply
                    )

    @anjani.on_command("setwelcome", admin_only=True)
    async def set_welcome(self, message):
        """ Set chat welcome message """
        chat = message.chat
        if not message.reply_to_message:
            return await message.reply_text(
                await self.text(chat.id, "err-reply-to-msg")
            )
        msg = message.reply_to_message
        await Greeting.set_custom_welcome(chat.id, msg.text)
        await message.reply_text(await self.text(chat.id, "cust-welcome-set"))

    @anjani.on_command("resetwelcome", admin_only=True)
    async def reset_welcome(self, message):
        """ Reset saved welcome message """
        chat = message.chat
        await Greeting.set_custom_welcome(chat.id, await Greeting.default_welc(chat.id))
        await message.reply_text(await self.text(chat.id, "reset-welcome"))

    @anjani.on_command("welcome", admin_only=True)
    async def view_welcome(self, message):
        """ View current welcome message """
        chat_id = message.chat.id
        if len(message.command) >= 1:
            arg = message.command[0]
            if arg in ["yes", "on"]:
                await Greeting.set_welc_pref(chat_id, True)
                return await message.reply_text(await self.text(chat_id, "welcome-set", "on"))
            elif arg in ["no", "off"]:
                await Greeting.set_welc_pref(chat_id, False)
                return await message.reply_text(await self.text(chat_id, "welcome-set", "off"))
            else:
                return await message.reply_text(await self.text(chat_id, "err-invalid-option"))
        sett, welc_text, clean_serv = await Greeting.full_welcome(chat_id)
        text = await self.text(
            chat_id,
            "view-welcome",
            sett,
            clean_serv
        )
        await message.reply_text(text)
        await message.reply_text(welc_text)

    @anjani.on_command("cleanservice", admin_only=True)
    async def cleanserv(self, message):
        """ Clean service message on new members """
        chat_id = message.chat.id
        if len(message.command) >= 1:
            arg = message.command[0]
            if arg in ["yes", "on"]:
                await Greeting.set_cleanserv(chat_id, True)
                await message.reply_text(await self.text(chat_id, "clean-serv-set", "on"))
            elif arg in ["no", "off"]:
                await Greeting.set_cleanserv(chat_id, False)
                await message.reply_text(await self.text(chat_id, "clean-serv-set", "off"))
            else:
                await message.reply_text(await self.text(chat_id, "err-invalid-option"))
        else:
            await message.reply_Text("Usage is on/yes or off/no")
