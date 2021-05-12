""" PyroClient """
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

import importlib
import logging
import pkgutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import pyrogram
from pyrogram.errors import AccessTokenExpired, AccessTokenInvalid

from ..utils import BotConfig
from . import pool
from .base import Base
from .client import Client

if TYPE_CHECKING:
    from .anjani import Anjani

LOG = logging.getLogger(__name__)


class TelegramBot(Base):
    """Extended `~pyrogram.Client`"""

    client: pyrogram.Client
    get_config: BotConfig

    executor: ThreadPoolExecutor
    identifier: int
    name: str
    staff: Dict[str, Union[str, int]]
    stopping: bool
    username: str

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        self.get_config = BotConfig()
        self.staff = {}

        super().__init__(**kwargs)

    async def init_client(self: "Anjani") -> None:
        """Initialize pyrogram client"""
        api_id = self.get_config.api_id
        if api_id == 0:
            raise TypeError("API ID is required")

        api_hash = self.get_config.api_hash
        if not isinstance(api_hash, str):
            raise TypeError("API HASH must be a string")

        bot_token = self.get_config.bot_token
        if not isinstance(bot_token, str):
            raise TypeError("BOT TOKEN must be a string")

        self.client = Client(
            self,
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token,
            session_name=":memory:",
        )
        owner = self.get_config.owner_id

        self.staff = {"owner": owner}

    async def start(self: "Anjani") -> None:
        """Start client"""
        LOG.info("Starting Bot Client...")
        try:
            await self.init_client()
        except TypeError as err:
            LOG.critical(err)
            await self.stop()
            return

        # Initialize pool
        self.client.executor.shutdown()
        self.client.executor = pool.start()

        await self.connect_db("AnjaniBot")
        self._load_language()
        try:
            subplugins = [
                importlib.import_module("anjani_bot.plugins." + info.name, __name__)
                for info in pkgutil.iter_modules(["anjani_bot/plugins"])
            ]
        except Exception as err:  # pylint: disable=broad-except
            traceback.print_exc()
            LOG.critical(err)
            await self.loop.stop()
        self.load_all_plugins(subplugins)
        try:
            await self.client.start()
        except (AccessTokenInvalid, AccessTokenExpired) as err:
            LOG.critical(err)
            self.loop.stop()
        await self._load_all_attribute()
        await self.channel_log("Bot started successfully...")

    async def run(self: "Anjani") -> None:
        """Run PyroClient"""
        try:
            # Start client
            try:
                await self.start()
            except KeyboardInterrupt:
                LOG.warning("Received interrupt while connecting")
                return

            # idle until disconnected
            LOG.info("Idling... Press Ctrl+V to stop")
            await pyrogram.idle()
        finally:
            await self.stop()

    def redact_message(self, text: str) -> str:
        """Secure any secret variable"""
        api_id = str(self.get_config.api_id)
        api_hash = self.get_config.api_hash
        bot_token = self.get_config.bot_token
        db_uri = self.get_config.db_uri
        spamwatch_api = self.get_config.spamwatch_api

        if api_id in text:
            text = text.replace(api_id, "[REDACTED]")
        if api_hash is not None and api_hash in text:
            text = text.replace(api_hash, "[REDACTED]")
        if bot_token is not None and bot_token in text:
            text = text.replace(bot_token, "[REDACTED]")
        if db_uri is not None and db_uri in text:
            text = text.replace(db_uri, "[REDACTED]")
        if spamwatch_api is not None and spamwatch_api in text:
            text = text.replace(spamwatch_api, "[REDACTED]")

        return text

    async def _load_all_attribute(self) -> None:
        """Load all client attributes"""
        bot = await self.client.get_me()
        self.identifier = bot.id
        self.username = bot.username
        if bot.last_name:
            self.name = bot.first_name + " " + bot.last_name
        else:
            self.name = bot.first_name

        _db = self.get_collection("STAFF")
        self.staff.update({"dev": [], "sudo": []})
        async for i in _db.find():
            self.staff[i["rank"]].append(i["_id"])

    @property
    def staff_id(self) -> List[int]:
        """Get bot staff ids as a list"""
        _id = [self.staff.get("owner")]
        _id.extend(self.staff.get("dev") + self.staff.get("sudo"))
        return _id

    async def channel_log(
        self,
        text: str,
        parse_mode: Optional[str] = object,
        disable_web_page_preview: bool = None,
        disable_notification: bool = None,
        reply_markup: Union[
            "pyrogram.types.InlineKeyboardMarkup",
            "pyrogram.types.ReplyKeyboardMarkup",
            "pyrogram.types.ReplyKeyboardRemove",
            "pyrogram.types.ForceReply",
        ] = None,
    ) -> Union["pyrogram.types.Message", None]:
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
        """
        log_channel = self.get_config.log_channel
        if log_channel == 0:
            LOG.warning(f"LOG_CHANNEL is empty nor valid, message '{text}' not sent.")
            return

        try:
            await self.client.send_message(
                chat_id=log_channel,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
            )
        except ValueError as err:
            LOG.error(f"Invalid LOG_CHANNEL: {err}")
