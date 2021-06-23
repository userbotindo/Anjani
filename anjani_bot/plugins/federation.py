"""Bot Federation Tools"""
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
import logging
import os
import time
from datetime import datetime
from typing import Union

from motor.motor_asyncio import AsyncIOMotorCursor
from pyrogram import filters
from pyrogram.errors import ChatAdminRequired
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from anjani_bot import listener, plugin
from anjani_bot.utils import (
    ParsedChatMember,
    extract_user,
    extract_user_and_text,
    rand_key,
)

LOGGER = logging.getLogger(__name__)


class FedBase:
    # declaring collection as a class member cause used by other.
    feds_db = listener.__bot__.get_collection("FEDERATIONS")

    async def __on_load__(self):
        self.lock = asyncio.Lock()

    async def __migrate__(self, old_chat_id, new_chat_id):
        async with self.lock:
            await self.feds_db.update_one(
                {"chats": old_chat_id}, {"$set": {"chats.$": new_chat_id}}
            )

    @staticmethod
    def is_fed_admin(fed_data: dict, user_id) -> bool:
        """Check federation admin"""
        return user_id == fed_data["owner"] or user_id in fed_data.get("admins", [])

    @classmethod
    async def get_fed_bychat(cls, chat_id):
        """Get fed data from chat id"""
        return await cls.feds_db.find_one({"chats": chat_id})

    async def get_fed_byowner(self, user_id):
        """Get fed data from user id"""
        return await self.feds_db.find_one({"owner": user_id})

    async def get_fed(self, fid):
        """Get fed data"""
        return await self.feds_db.find_one({"_id": fid})

    async def fban_user(self, fid, user_id, fullname=None, reason=None, ban: bool = True):
        """Remove or Add banned user"""
        if ban:
            action = "$set"
            data = {"name": fullname, "reason": reason, "time": time.time()}
        else:
            action = "$unset"
            data = 1
        async with self.lock:
            await self.feds_db.update_one(
                {"_id": fid}, {action: {f"banned.{int(user_id)}": data}}, upsert=True
            )

    async def check_fban(self, user_id) -> Union[AsyncIOMotorCursor, bool]:
        """Check user banned list"""
        doc = await self.feds_db.count_documents({f"banned.{user_id}": {"$exists": True}})
        return (
            self.feds_db.find(
                {f"banned.{user_id}": {"$exists": True}},
                projection={f"banned.{user_id}": 1, "name": 1, "chats": 1},
            )
            if doc
            else False
        )

    @staticmethod
    def parse_date(timestamp: float) -> str:
        """get a date format from a timestamp"""
        return datetime.fromtimestamp(timestamp).strftime("%Y %b %d %H:%M UTC")


class Federation(plugin.Plugin, FedBase):
    name = "Federations"
    helpable = True

    @listener.on("newfed")
    async def new_fed(self, message):
        """Create a new federations"""
        chat_id = message.chat.id
        if message.chat.type != "private":
            return await message.reply_text(await self.bot.text(chat_id, "error-chat-not-private"))

        if message.command:
            fed_name = (" ".join(message.command)).strip()
            fed_id = rand_key()
            owner_id = message.from_user.id

            check = await self.feds_db.find_one({"owner": owner_id})
            if check:
                return await message.reply_text(await self.bot.text(chat_id, "federeation-limit"))

            async with self.lock:
                await self.feds_db.insert_one(
                    {"_id": fed_id, "name": fed_name, "owner": owner_id, "log": owner_id}
                )
            LOGGER.debug(f"Created new fed {fed_name}({fed_id}) by {message.from_user.username}")
            text = await self.bot.text(chat_id, "new-federation", fed_name=fed_name, fed_id=fed_id)
            await asyncio.gather(
                message.reply_text(text),
                self.bot.channel_log(
                    f"Created new federation **{fed_name}** with ID: **{fed_id}**"
                ),
            )
        else:
            await message.reply_text(await self.bot.text(chat_id, "need-fed-name"))

    @listener.on("delfed")
    async def del_fed(self, message):
        """Delete federations"""
        chat_id = message.chat.id
        if message.chat.type != "private":
            return await message.reply_text(await self.bot.text(chat_id, "error-chat-not-private"))

        user_id = message.from_user.id
        feds = await self.feds_db.find_one({"owner": user_id})
        if not feds:
            return await message.reply_text(await self.bot.text(chat_id, "user-no-feds"))

        await message.reply_text(
            await self.bot.text(chat_id, "del-fed-confirm", feds["name"]),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=await self.bot.text(chat_id, "fed-confirm-text"),
                            callback_data=f"rmfed_{feds['_id']}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=await self.bot.text(chat_id, "fed-abort-text"),
                            callback_data="rmfed_abort",
                        )
                    ],
                ]
            ),
        )

    @listener.on(filters=filters.regex(r"rmfed_(.*?)"), update="callbackquery")
    async def del_fed_query(self, query):
        """Delete federation button listener"""
        chat_id = query.message.chat.id
        fed_id = query.data.split("_")[1]
        if fed_id == "abort":
            return await query.message.edit_text(
                await self.bot.text(chat_id, "fed-delete-canceled")
            )
        LOGGER.debug(f"Deleting federation {fed_id}")
        async with self.lock:
            data = await self.feds_db.find_one_and_delete({"_id": fed_id})
        await query.message.edit_text(await self.bot.text(chat_id, "fed-delete-done", data["name"]))

    @listener.on("joinfed", admin_only=True)
    async def join_fed(self, message):
        """Join a federation in chats"""
        chat_id = message.chat.id
        user_id = message.from_user.id
        admins = await message.chat.get_member(user_id)
        if not (admins.status == "creator" or user_id == self.bot.staff["owner"]):
            return await message.reply_text(await self.bot.text(chat_id, "err-group-creator-cmd"))

        if message.command:
            if await self.get_fed_bychat(chat_id):
                return await message.reply_text(await self.bot.text(chat_id, "fed-cant-two-feds"))
            fid = message.command[0]
            fdata = await self.get_fed(fid)
            if not fdata:
                return await message.reply_text(await self.bot.text(chat_id, "fed-invalid-id"))
            if chat_id in fdata.get("chats", []):
                return await message.reply_text(
                    await self.bot.text(chat_id, "fed-already-connected")
                )

            async with self.lock:
                await self.feds_db.update_one({"_id": fid}, {"$push": {"chats": chat_id}})
            await message.reply_text(
                await self.bot.text(chat_id, "fed-chat-joined-info", fdata["name"])
            )
            if flog := fdata.get("log", None):
                await self.bot.client.send_message(flog, "")

    @listener.on("leavefed", admin_only=True)
    async def leave_fed(self, message):
        """Leave a federation in chats"""
        chat_id = message.chat.id
        user_id = message.from_user.id
        admins = await message.chat.get_member(user_id)
        if not (admins.status == "creator" or user_id == self.bot.staff["owner"]):
            return await message.reply_text(await self.bot.text(chat_id, "err-group-creator-cmd"))

        if message.command:
            fid = message.command[0]
            check = await self.get_fed(fid)
            if not check:
                return await message.reply_text(await self.bot.text(chat_id, "fed-invalid-id"))
            if chat_id not in check.get("chats"):
                return await message.reply_text(await self.bot.text(chat_id, "fed-not-connected"))

            async with self.lock:
                await self.feds_db.update_one({"_id": fid}, {"$pull": {"chats": chat_id}})
            await message.reply_text(
                await self.bot.text(chat_id, "fed-chat-leave-info", check["name"])
            )

    @listener.on(["fpromote", "fedpromote"])
    async def promote_fadmin(self, message):
        """Promote user to fed admin"""
        chat_id = message.chat.id
        if message.chat.type == "private":
            return await message.reply_text(await self.bot.text(chat_id, "err-chat-groups"))

        user_id = message.from_user.id
        to_promote, _ = extract_user_and_text(message)
        if not to_promote:
            return await message.reply_text(await self.bot.text(chat_id, "fed-no-promote-user"))
        new_admin = await extract_user(self.bot.client, to_promote)
        to_promote = new_admin.id
        fed_data = await self.get_fed_bychat(chat_id)
        if not fed_data:
            return await message.reply_text(await self.bot.text(chat_id, "fed-no-fed-chat"))
        if user_id != fed_data["owner"]:
            return await message.reply_text(await self.bot.text(chat_id, "fed-owner-only-promote"))
        if to_promote == fed_data["owner"]:
            return await message.reply_text(await self.bot.text(chat_id, "fed-already-owner"))
        if to_promote in fed_data.get("admins", []):
            return await message.reply_text(await self.bot.text(chat_id, "fed-already-admin"))

        async with self.lock:
            await self.feds_db.update_one(
                {"_id": fed_data["_id"]}, {"$push": {"admins": to_promote}}
            )
        await message.reply_text(await self.bot.text(chat_id, "fed-promote-done"))
        if flog := fed_data.get("log", None):
            await self.bot.client.send_message(
                flog,
                "**New Fed Promotion**\n"
                f"**Fed: **{fed_data['name']}\n"
                f"**Promoted FedAdmin: {new_admin.mention}**\n"
                f"**User ID: **{to_promote}",
            )

    @listener.on(["fdemote", "feddemote"])
    async def demote_fadmin(self, message):
        """Demote user to fed admin"""
        chat_id = message.chat.id
        if message.chat.type == "private":
            return await message.reply_text(await self.bot.text(chat_id, "err-chat-groups"))

        user_id = message.from_user.id
        to_demote, _ = extract_user_and_text(message)
        if not to_demote:
            return await message.reply_text(await self.bot.text(chat_id, "fed-no-demote-user"))
        demote_user = await extract_user(self.bot.client, to_demote)
        to_demote = demote_user.id
        fed_data = await self.get_fed_bychat(chat_id)
        if not fed_data:
            return await message.reply_text(await self.bot.text(chat_id, "fed-no-fed-chat"))
        if user_id != fed_data["owner"]:
            return await message.reply_text(await self.bot.text(chat_id, "fed-owner-only-demote"))
        if to_demote == fed_data["owner"]:
            return await message.reply_text(await self.bot.text(chat_id, "fed-already-owner"))
        if to_demote not in fed_data.get("admins", []):
            return await message.reply_text(await self.bot.text(chat_id, "fed-user-not-admin"))

        async with self.lock:
            await self.feds_db.update_one(
                {"_id": fed_data["_id"]}, {"$pull": {"admins": to_demote}}
            )
        await message.reply_text(await self.bot.text(chat_id, "fed-demote-done"))
        if flog := fed_data.get("log", None):
            await self.bot.client.send_message(
                flog,
                "**New Fed Demotion**\n"
                f"**Fed: **{fed_data['name']}\n"
                f"**Promoted FedAdmin: {demote_user.mention}**\n"
                f"**User ID: **{to_demote}",
            )

    @listener.on("fedinfo")
    async def fed_info(self, message):
        """Fetch federation info"""
        chat_id = message.chat.id
        if message.command:
            fdata = await self.get_fed(message.command[0])
            if not fdata:
                return await message.reply_text(chat_id, "fed-invalid-id")
        elif message.chat.type != "private":
            fdata = await self.get_fed_bychat(chat_id)
            if not fdata:
                return await message.reply_text(
                    await self.bot.text(chat_id, "fed-no-fed-chat")
                    + "\n"
                    + await self.bot.text(chat_id, "fed-specified-id")
                )
        else:
            return await message.reply_text(await self.bot.text(chat_id, "fed-specified-id"))

        owner = await extract_user(self.bot.client, fdata["owner"])
        await message.reply_text(
            await self.bot.text(
                chat_id,
                "fed-info-text",
                fdata["_id"],
                fdata["name"],
                owner.mention,
                len(fdata.get("admins", [])),
                len(fdata.get("banned", [])),
                len(fdata.get("chats", [])),
            )
        )

    @listener.on("fadmins")
    async def fed_admins(self, message):
        """Fetch federation admins"""
        chat_id = message.chat.id
        fdata = None
        if message.command:
            fdata = await self.get_fed(message.command[0])
            text = await self.bot.text(chat_id, "fed-invalid-id")
        else:
            fdata = await self.get_fed_bychat(chat_id)
            text = await self.bot.text(chat_id, "fed-no-fed-chat")

        if not fdata:
            return await message.reply_text(text)
        user_id = message.from_user.id
        if not self.is_fed_admin(fdata, user_id):
            return await message.reply_text(await self.bot.text(chat_id, "fed-admin-only"))

        owner = await extract_user(self.bot.client, fdata["owner"])

        text = await self.bot.text(chat_id, "fed-admin-text", fdata["name"], owner.mention)
        if len(fdata.get("admins", [])) != 0:
            text += "Admins:\n"
            for admin in fdata["admins"]:
                user = await extract_user(self.bot.client, admin)
                text += f" • {user.mention}\n"
        else:
            text += await self.bot.text(chat_id, "fed-no-admin")
        await message.reply_text(text)

    @listener.on("fban")
    async def fed_ban(self, message):
        """Fed ban a user"""
        chat_id = message.chat.id
        if message.chat.type == "private":
            return await message.reply_text(await self.bot.text(chat_id, "err-chat-groups"))

        banner = message.from_user
        fed_data = await self.get_fed_bychat(chat_id)
        if not fed_data:
            return await message.reply_text(await self.bot.text(chat_id, "fed-no-fed-chat"))

        if not self.is_fed_admin(fed_data, banner.id):
            return await message.reply_text(await self.bot.text(chat_id, "fed-admin-only"))

        to_ban, reason = extract_user_and_text(message)
        if not to_ban:
            return await message.reply_text(await self.bot.text(chat_id, "fed-no-ban-user"))

        user = await extract_user(self.bot.client, to_ban)
        user_id = user.id
        if user_id == self.bot.identifier:
            return await message.reply_text(await self.bot.text(chat_id, "fed-ban-self"))
        if self.is_fed_admin(fed_data, user_id):
            return await message.reply_text(await self.bot.text(chat_id, "fed-ban-owner"))
        if user_id in self.bot.staff_id or user_id in (777000, 1087968824):
            return await message.reply_text(await self.bot.text(chat_id, "fed-ban-protected"))

        if not reason:
            reason = "No reason given."
        update = False
        if str(user_id) in fed_data.get("banned", {}).keys():
            update = True

        banned_user = ParsedChatMember(user)
        await self.fban_user(fed_data["_id"], user_id, banned_user.fullname, reason, True)
        if update:
            text = await self.bot.text(
                chat_id,
                "fed-ban-info-update",
                fed_data["name"],
                banner.mention,
                banned_user.mention,
                user_id,
                fed_data["banned"][str(user_id)]["reason"],
                reason,
            )
        else:
            text = await self.bot.text(
                chat_id,
                "fed-ban-info",
                fed_data["name"],
                banner.mention,
                banned_user.mention,
                user_id,
                reason,
            )

        await message.reply_text(text, disable_web_page_preview=True)
        LOGGER.debug(f"New fedban {user_id} on {fed_data['_id']}")
        for chats in fed_data["chats"]:
            try:
                await self.bot.client.kick_chat_member(chats, user_id)
            except ChatAdminRequired:
                pass
        # send message to federation log
        flog = fed_data.get("log", None)
        if flog:
            await self.bot.client.send_message(flog, text, disable_web_page_preview=True)

    @listener.on("unfban")
    async def unfban_user(self, message):
        """Unban a user on federation"""
        chat_id = message.chat.id
        if message.chat.type == "private":
            return await message.reply_text(await self.bot.text(chat_id, "err-chat-groups"))

        banner = message.from_user
        fed_data = await self.get_fed_bychat(chat_id)
        if not fed_data:
            return await message.reply_text(await self.bot.text(chat_id, "fed-no-fed-chat"))

        if not self.is_fed_admin(fed_data, banner.id):
            return await message.reply_text(await self.bot.text(chat_id, "fed-admin-only"))

        to_unban, _ = extract_user_and_text(message)
        if not to_unban:
            return await message.reply_text(await self.bot.text(chat_id, "fed-no-ban-user"))

        user = await extract_user(self.bot.client, to_unban)
        if str(user.id) not in fed_data.get("banned").keys():
            return await message.reply_text(await self.bot.text(chat_id, "fed-user-not-banned"))

        await self.fban_user(fed_data["_id"], user.id, ParsedChatMember(user).fullname, ban=False)

        text = await self.bot.text(
            chat_id, "fed-unban-info", fed_data["name"], banner.mention, user.mention, user.id
        )
        await message.reply_text(text)
        LOGGER.debug(f"Unfedban {user.id} on {fed_data['_id']}")
        for chats in fed_data["chats"]:
            await self.bot.client.unban_chat_member(chats, user.id)
        # send message to federation log
        flog = fed_data.get("log", None)
        if flog:
            await self.bot.client.send_message(flog, text, disable_web_page_preview=True)

    @listener.on(["fedstats", "fstats"])
    async def fed_stats(self, message):
        """Get user status"""
        chat_id = message.chat.id
        user_id, _ = extract_user_and_text(message)
        if isinstance(user_id, str):
            user_id = (await extract_user(self.bot.client, user_id)).id
        if not user_id:
            user_id = message.from_user.id

        # <user_Id> <fed_id>
        if len(message.command) == 2 and message.command[0].isdigit():
            fid = message.command[1]
            data = await self.get_fed(fid)
            if not data:
                return await message.reply_text(await self.bot.text(chat_id, "fed-invalid-id"))
            if message.command[0] in data.get("banned", {}):
                res = data["banned"][str(message.command[0])]
                await message.reply_text(
                    await self.bot.text(
                        chat_id, "fed-stat-banned", res["reason"], self.parse_date(res["time"])
                    )
                )
            else:
                return await message.reply_text(await self.bot.text(chat_id, "fed-stat-not-banned"))

        # <user_Id>
        else:
            data = await self.check_fban(user_id)
            if data:
                text = await self.bot.text(chat_id, "fed-stat-multi")
                async for bans in data:
                    text += await self.bot.text(
                        chat_id,
                        "fed-stat-multi-info",
                        bans["name"],
                        bans["_id"],
                        bans["nammed"][str(user_id)]["reason"],
                    )
            else:
                text = await self.bot.text(chat_id, "fed-stat-multi-not-banned")
            await message.reply_text(text)

    @listener.on("fbackup", filters.private)
    async def backup_fedband(self, message):
        """Backup federation ban list"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        feds = await self.feds_db.find_one({"owner": user_id})
        if not feds:
            return await message.reply_text(await self.bot.text(chat_id, "user-no-feds"))

        banned_list = feds["banned"]
        file_name = f"{self.bot.get_config.download_path}{feds['name']}.csv"
        LOGGER.debug(f"Backing up fed data of {feds['_id']}")
        with open(file_name, "w") as file:
            for user in banned_list:
                ban_data = banned_list[str(user)]
                file.writelines(
                    f"{user},{ban_data['name']},{ban_data['reason']},{ban_data['time']}"
                )

        await message.reply_document(file_name)
        os.remove(file_name)

    @listener.on("fexport", filters.private)
    async def restore_fban(self, message):
        """Restore a backup bans"""
        chat_id = message.chat.id
        if not (message.reply_to_message and message.reply_to_message.document):
            return await message.reply_text(await self.bot.text(chat_id, "no-backup-file"))
        user_id = message.from_user.id
        data = await self.feds_db.find_one({"owner": user_id})
        if not data:
            return await message.reply_text(await self.bot.text(chat_id, "user-no-feds"))

        LOGGER.debug(f"Restoring fed ban of {data['_id']}")
        file = await message.reply_to_message.download(self.bot.get_config.download_path)
        fid = data["_id"]
        with open(file, "r") as buff:
            for line in buff:
                data = line.split(",")
                await self.fban_user(fid, data[0], data[1], data[2], True)
        await message.reply_text(await self.bot.text(chat_id, "fed-restore-done"))
        os.remove(file)

    @listener.on("myfeds", filters.private)
    async def self_feds(self, message):
        """Get current users federation"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        owned_fed = await self.feds_db.find_one({"owner": user_id})
        text = ""
        if owned_fed:
            text += await self.bot.text(chat_id, "fed-myfeds-owner")
            text += f"- `{owned_fed['_id']}`: {owned_fed['name']}\n"
        fed_admin = self.feds_db.find({"admins": user_id})
        fed_list = await fed_admin.to_list(None)
        if fed_list:
            text += await self.bot.text(chat_id, "fed-myfeds-admin")
            for fed in fed_list:
                text += f"- `{fed['_id']}`: {fed['name']}\n"
        if not text:
            text = await self.bot.text(chat_id, "fed-myfeds-no-admin")
        await message.reply_text(text)

    @listener.on("setfedlog")
    async def setlog(self, message):
        chat_id = message.chat.id
        if message.chat.type == "channel":
            if not message.command:
                return await message.reply_text(await self.bot.text(chat_id, "fed-set-log-args"))
            fed_data = await self.get_fed(message.command[0])
            if not fed_data:
                return await message.reply_text(await self.bot.text(chat_id, "Fed not found!"))
            await message.reply_text(
                await self.bot.text(chat_id, "fed-check-identity"),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Click to confirm identity",
                                callback_data=f"logfed_{fed_data['owner']}_{fed_data['_id']}",
                            )
                        ],
                    ]
                ),
            )

        elif message.chat.type in ["group", "supergroup"]:
            owned_fed = await self.get_fed_byowner(message.from_user.id)
            if not owned_fed:
                return await message.reply_text(await self.bot.text(chat_id, "user-no-feds"))
            await self.feds_db.update_one({"_id": owned_fed["_id"]}, {"$set": {"log": chat_id}})
            await message.reply_text(
                await self.bot.text(chat_id, "fed-log-set-group", owned_fed["name"])
            )
        else:
            await message.reply_text(await self.bot.text(chat_id, "err-chat-groups"))

    @listener.on(filters=filters.regex(r"logfed_(.*?)"), update="callbackquery")
    async def confirm_log_fed(self, query):
        chat_id = query.message.chat.id
        user_id = query.from_user.id
        _, owner_id, fid = query.data.split("_")
        if user_id != int(owner_id):
            return await query.edit_message_text(
                await self.bot.text(chat_id, "fed-invalid-identity")
            )
        fed_data = await self.feds_db.find_one_and_update({"_id": fid}, {"$set": {"log": chat_id}})
        await query.edit_message_text(
            await self.bot.text(chat_id, "fed-log-set-chnl", fed_data["name"])
        )

    @listener.on("unsetfedlog")
    async def unsetlog(self, message):
        chat_id = message.chat.id
        if message.chat.type == "private":
            user_id = message.from_user.id
            fed_data = await self.get_fed_byowner(user_id)
            if not fed_data:
                await message.reply_text(await self.bot.text(chat_id, "user-no-feds"))
            await self.feds_db.update_one({"_id": fed_data["_id"]}, {"$set": {"log": None}})
            await message.reply_text(
                await self.bot.text(chat_id, "fed-log-unset", fed_data["name"])
            )
        else:
            await message.reply_text(await self.bot.text(chat_id, "err-chat-private"))
