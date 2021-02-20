import asyncio
import importlib
import logging
import os
import pkgutil

from typing import TYPE_CHECKING, Any, List, Optional, Union

from .base import Base

if TYPE_CHECKING:
    from .anjani import Anjani

import pyrogram
from pyrogram import types

log = logging.getLogger(__name__)


class TelegramBot(Base):
    client: pyrogram.Client

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def init_client(self: "Anjani") -> None:
        try:
            api_id = int(self.getConfig("API_ID"))
        except ValueError:
            raise("API ID is not a valid integer")

        api_hash = self.getConfig("API_HASH")
        if not isinstance(api_hash, str):
            raise TypeError("API HASH must be a string")

        bot_token = self.getConfig("BOT_TOKEN")
        if not isinstance(bot_token, str):
            raise TypeError("BOT TOKEN must be a string")

        self.client = pyrogram.Client(
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token,
            session_name=":memory:"
        )

        self.staff = {"owner": self.getConfig("OWNER_ID")}

    async def start(self: "Anjani"):
        """ Start client """
        log.info("Starting Bot Client...")
        await self.init_client()
        await self.connect_db("AnjaniBot")
        self._load_language()
        subplugins = [
            importlib.import_module("anjani_bot.plugins." + info.name, __name__)
            for info in pkgutil.iter_modules(["anjani_bot/plugins"])
        ]
        self.load_all_modules(subplugins)
        await self.client.start()
        await self._load_all_attribute()
        await self.channel_log("Bot started successfully...")

    async def run(self: "Anjani") -> None:
        try:
            # Start client
            try:
                await self.start()
            except KeyboardInterrupt:
                log.warning("Received interrupt while connecting")
                return

            # idle until disconnected
            await pyrogram.idle()
        finally:
            await self.stop()

    def getConfig(self: "Anjani", name: str) -> Union[str, int]:
        return os.environ.get(name)

    def redact_message(self, text: str) -> str:
        api_id = self.getConfig("API_ID")
        api_hash = self.getConfig("API_HASH")
        bot_token = self.getConfig("BOT_TOKEN")

        if api_id in text:
            text = text.replace(api_id, "[REDACTED]")
        if api_hash in text:
            text = text.replace(api_hash, "[REDACTED]")
        if bot_token in text:
            text = text.replace(bot_token, "[REDACTED]")

        return text

    @property
    def staff_id(self) -> List[int]:
        """ Get bot staff ids as a list """
        _id = [self.staff.get("owner")]
        _id.extend(self.staff.get("dev") + self.staff.get("sudo"))
        return _id

    async def _load_all_attribute(self) -> None:
        """ Load all client attributes """
        bot = await self.client.get_me()
        self.identifier = bot.id
        self.username = bot.username
        if bot.last_name:
            self.name = bot.first_name + " " + bot.last_name
        else:
            self.name = bot.first_name

        _db = self.get_collection("STAFF")
        self.staff.update({'dev': [], 'sudo': []})
        async for i in _db.find():
            self.staff[i["rank"]].append(i["_id"])

    async def channel_log(
            self,
            text: str,
            parse_mode: Optional[str] = object,
            disable_web_page_preview: bool = None,
            disable_notification: bool = None,
            reply_markup: Union[
                "types.InlineKeyboardMarkup",
                "types.ReplyKeyboardMarkup",
                "types.ReplyKeyboardRemove",
                "types.ForceReply"
            ] = None
        ) -> Union["types.Message", None]:
        """Shortcut method to send message to log channel.

        Parameters:
            text (`str`):
                Text of the message to be sent.

            parse_mode (`str`, *optional*):
                By default, texts are parsed using both Markdown and HTML styles.
                You can combine both syntaxes together.
                Pass "markdown" or "md" to enable Markdown-style parsing only.
                Pass "html" to enable HTML-style parsing only.
                Pass None to completely disable style parsing.

            disable_web_page_preview (`bool`, *optional*):
                Disables link previews for links in this message.

            disable_notification (`bool`, *optional*):
                Sends the message silently.
                Users will receive a notification with no sound.

            reply_markup (
                :obj:`~InlineKeyboardMarkup` | :obj:`~ReplyKeyboardMarkup` |
                :obj:`~ReplyKeyboardRemove` | :obj:`~ForceReply`, *optional*
                ):
                Additional interface options. An object for an inline keyboard,
                custom reply keyboard, instructions to remove reply keyboard or
                to force a reply from the user.

        Returns:
            :obj:`~types.Message`: On success, the sent text message is returned.
        """
        if self._log_channel == 0:
            log.warning("No LOG_CHANNEL var! message '%s' not sended.", text)
            return None

        return await self.client.send_message(
            chat_id=self._log_channel,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            reply_markup=reply_markup
        )
