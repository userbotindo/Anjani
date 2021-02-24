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
from typing import ClassVar, Tuple, Union

from motor.motor_asyncio import AsyncIOMotorCollection
from pyrogram import filters

from anjani_bot import listener, plugin


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

    async def get_members(self, client, chat_id):
        """ Count chat member """
        self.count = await client.get_chat_members_count(chat_id)


class RawGreeting:
    welcome_db: AsyncIOMotorCollection
    lock: asyncio.locks.Lock

    async def __on_load__(self):
        self.welcome_db = self.bot.get_collection("WELCOME")
        self.lock = asyncio.Lock()

    async def __migrate__(self, old_chat, new_chat):
        async with self.lock:
            await self.welcome_db.update_one(
                {'chat_id': old_chat},
                {"$set": {
                    'chat_id': new_chat
                }},
            )

    async def default_welc(self, chat_id):
        """ Bot default welcome """
        return await self.bot.text(chat_id, "default-welcome", noformat=True)

    @staticmethod
    async def parse_user(user) -> NewChatMember:
        """ Get user attribute """
        parsed_user = NewChatMember(user)
        return parsed_user

    async def full_welcome(self, chat_id) -> Tuple[bool, str, bool]:
        """ Get chat full welcome data """
        sett = await self.welc_pref(chat_id)
        text = await self.welc_msg(chat_id)
        clean_serv = await self.clean_service(chat_id)
        return sett, text, clean_serv

    async def welc_pref(self, chat_id) -> bool:
        """ Get chat welcome setting """
        setting = await self.welcome_db.find_one({'chat_id': chat_id})
        return setting.get("should_welcome", True) if setting else True

    async def welc_msg(self, chat_id) -> str:
        """ Get chat welcome string """
        data = await self.welcome_db.find_one({'chat_id': chat_id})
        if data:
            return data.get("custom_welcome", await self.default_welc(chat_id))
        return await self.default_welc(chat_id)

    async def clean_service(self, chat_id) -> bool:
        """ Fetch clean service setting """
        clean = await self.welcome_db.find_one({'chat_id': chat_id})
        if clean:
            return clean.get("clean_service", False)
        return False

    async def set_custom_welcome(self, chat_id, text):
        """ Set custome welcome """
        async with self.lock:
            await self.welcome_db.update_one(
                {'chat_id': chat_id}, {"$set": {
                    'custom_welcome': text
                }},
                upsert=True)

    async def del_custom_welcome(self, chat_id):
        """ Delete custom welcome msg """
        async with self.lock:
            await self.welcome_db.update_one(
                {'chat_id': chat_id}, {"$unset": {
                    'custom_welcome': ""
                }})

    async def set_cleanserv(self, chat_id, setting):
        """ Clean service db """
        async with self.lock:
            await self.welcome_db.update_one(
                {'chat_id': chat_id}, {"$set": {
                    'clean_service': setting
                }},
                upsert=True)

    async def set_welc_pref(self, chat_id, setting: bool):
        """ Turn on/off welcome in chats """
        async with self.lock:
            await self.welcome_db.update_one(
                {'chat_id': chat_id}, {"$set": {
                    'should_welcome': setting
                }},
                upsert=True)

    async def prev_welcome(self, chat_id, msg_id: int) -> Union[int, bool]:
        """ Save latest welcome msg_id and return previous msg_id"""
        async with self.lock:
            data = await self.welcome_db.find_one_and_update(
                {'chat_id': chat_id}, {"$set": {
                    'prev_welc': msg_id
                }},
                upsert=True)
        if data:
            return data.get("prev_welc", False)
        return False


class Greeting(plugin.Plugin, RawGreeting):
    name: ClassVar[str] = "Greetings"
    helpable: ClassVar[bool] = True

    @listener.on(filters=filters.new_chat_members, group=5, update="message")
    async def new_member(self, message):
        """ Greet new member """
        chat = message.chat
        new_members = message.new_chat_members

        should_welc = await self.welc_pref(chat.id)
        if should_welc:
            reply = message.message_id
            clean_serv = await self.clean_service(chat.id)
            if clean_serv:
                await message.delete()
                reply = False
            for new_member in new_members:
                if new_member.id == self.bot.identifier:
                    await self.bot.client.send_message(
                        chat.id,
                        await self.bot.text(chat.id, "bot-added"),
                        reply_to_message_id=reply)
                else:
                    welcome_text = await self.welc_msg(chat.id)
                    user = await self.parse_user(new_member)
                    await user.get_members(self.bot.client, chat.id)
                    formatted_text = welcome_text.format(
                        first=escape(user.first_name),
                        last=escape(new_member.last_name or user.first_name),
                        fullname=escape(user.fullname),
                        username=user.username,
                        mention=user.mention,
                        count=user.count,
                        chatname=escape(chat.title),
                        id=new_member.id)

                    msg = await self.bot.client.send_message(
                        chat.id, formatted_text, reply_to_message_id=reply)

                    prev_welc = await self.prev_welcome(
                        chat.id, msg.message_id)
                    if prev_welc:
                        await self.bot.client.delete_messages(
                            chat.id, prev_welc)

    @listener.on("setwelcome", admin_only=True)
    async def set_welcome(self, message):
        """ Set chat welcome message """
        chat = message.chat
        if not message.reply_to_message:
            return await message.reply_text(await self.bot.text(
                chat.id, "err-reply-to-msg"))
        msg = message.reply_to_message
        await self.set_custom_welcome(chat.id, msg.text)
        await message.reply_text(await self.bot.text(chat.id,
                                                     "cust-welcome-set"))

    @listener.on("resetwelcome", admin_only=True)
    async def reset_welcome(self, message):
        """ Reset saved welcome message """
        chat = message.chat
        await self.del_custom_welcome(chat.id)
        await message.reply_text(await self.bot.text(chat.id, "reset-welcome"))

    @listener.on("welcome", admin_only=True)
    async def view_welcome(self, message):
        """ View current welcome message """
        chat_id = message.chat.id
        if message.command:
            arg = message.command[0]
            if arg in ["yes", "on"]:
                await self.set_welc_pref(chat_id, True)
                return await message.reply_text(await self.bot.text(
                    chat_id, "welcome-set", "on"))
            if arg in ["no", "off"]:
                await self.set_welc_pref(chat_id, False)
                return await message.reply_text(await self.bot.text(
                    chat_id, "welcome-set", "off"))

            return await message.reply_text(await self.bot.text(
                chat_id, "err-invalid-option"))
        sett, welc_text, clean_serv = await self.full_welcome(chat_id)
        text = await self.bot.text(chat_id, "view-welcome", sett, clean_serv)
        await message.reply_text(text)
        await message.reply_text(welc_text)

    @listener.on("cleanservice", admin_only=True)
    async def cleanserv(self, message):
        """ Clean service message on new members """
        chat_id = message.chat.id
        if message.command:
            arg = message.command[0]
            if arg in ["yes", "on"]:
                await self.set_cleanserv(chat_id, True)
                await message.reply_text(await
                                         self.bot.text(chat_id,
                                                       "clean-serv-set", "on"))
            if arg in ["no", "off"]:
                await self.set_cleanserv(chat_id, False)
                await message.reply_text(await
                                         self.bot.text(chat_id,
                                                       "clean-serv-set",
                                                       "off"))
            await message.reply_text(await
                                     self.bot.text(chat_id,
                                                   "err-invalid-option"))
        else:
            await message.reply_text("Usage is on/yes or off/no")
