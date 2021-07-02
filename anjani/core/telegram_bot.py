import asyncio
import signal
from typing import (
    TYPE_CHECKING,
    Any,
    MutableMapping,
    Optional,
    Tuple,
    Type,
    Union,
)

from pyrogram import Client
from pyrogram.filters import Filter
from pyrogram.handlers import (
    CallbackQueryHandler,
    InlineQueryHandler,
    MessageHandler
)
from pyrogram.types import (
    CallbackQuery,
    InlineQuery,
    Message,
    User
)

from anjani import custom_filter, util
from .anjani_mixin_base import MixinBase

if TYPE_CHECKING:
    from .anjani_bot import Anjani

EventType = Union[CallbackQuery, InlineQuery, Message]
TgEventHandler = Union[CallbackQueryHandler,
                       InlineQueryHandler,
                       MessageHandler]


class TelegramBot(MixinBase):
    # Initialized during instantiation
    config: util.config.TelegramConfig
    _plugin_event_handlers: MutableMapping[str, Tuple[TgEventHandler, int]]
    _disconnect: bool
    loaded: bool

    # Initialized during startup
    client: Client
    prefix: str
    user: User
    uid: int
    start_time_us: int

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        self.config = util.config.TelegramConfig()
        self._plugin_event_handlers = {}
        self._disconnect = False
        self.loaded = False

        # Propagate initialization to other mixins
        super().__init__(**kwargs)

    async def init_client(self: "Anjani") -> None:
        api_id = self.config["api_id"]
        if not isinstance(api_id, int):
            raise TypeError("API ID must be an integer")

        api_hash = self.config["api_hash"]
        if not isinstance(api_hash, str):
            raise TypeError("API hash must be a string")

        bot_token = self.config["bot_token"]
        if not isinstance(bot_token, str):
            raise TypeError("Bot Token must be a string")

        # Initialize Telegram client with gathered parameters
        self.client = Client(
            session_name=":memory:", api_id=api_id, api_hash=api_hash,
            bot_token=bot_token
        )

    async def start(self: "Anjani") -> None:
        self.log.info("Starting")
        await self.init_client()

        # Register core command handler
        self.client.add_handler(MessageHandler(self.on_command,
                                               self.command_predicate()), -1)

        # Load plugin
        self.load_all_plugins()
        await self.dispatch_event("load")
        self.loaded = True


        # Start Telegram client
        try:
            await self.client.start()
        except AttributeError:
            self.log.error(
                "Unable to get input for authorization! Make sure all configuration are done before running the bot."
            )
            raise

        # Get info
        user = await self.client.get_me()
        if not isinstance(user, User):
            raise TypeError("Missing full self user information")
        self.user = user
        # noinspection PyTypeChecker
        self.uid = user.id

        # Record start time and dispatch start event
        self.start_time_us = util.time.usec()
        await self.dispatch_event("start", self.start_time_us)

        self.log.info("Bot is ready")

        # Dispatch final late start event
        await self.dispatch_event("started")

    async def idle(self: "Anjani") -> None:
        signals = {
            k: v
            for v, k in signal.__dict__.items()
            if v.startswith("SIG") and not v.startswith("SIG_")
        }

        def signal_handler(signum, __):

            self.log.info(f"Stop signal received ('{signals[signum]}').")
            self._disconnect = True

        for name in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT):
            signal.signal(name, signal_handler)

        while not self._disconnect:
            await asyncio.sleep(1)

    async def run(self: "Anjani") -> None:
        try:
            # Start client
            try:
                await self.start()
            except KeyboardInterrupt:
                self.log.warning("Received interrupt while connecting")
                return

            # Request updates, then idle until disconnected
            await self.idle()
        finally:
            # Make sure we stop when done
            await self.stop()

    def update_plugin_event(self: "Anjani",
                            name: str,
                            event_type: Type[TgEventHandler],
                            *,
                            filters: Optional[Filter] = None,
                            group: int = 0
    ) -> None:
        if name in self.listeners:
            # Add if there ARE listeners and it's NOT already registered
            if name not in self._plugin_event_handlers:

                async def event_handler(client: Client, event: EventType) -> None:  # skipcq: PYL-W0613
                    await self.dispatch_event(name, event)

                handler_info = (event_type(event_handler, filters), group)
                self.client.add_handler(*handler_info)
                self._plugin_event_handlers[name] = handler_info
        elif name in self._plugin_event_handlers:
            # Remove if there are NO listeners and it's ALREADY registered
            self.client.remove_handler(*self._plugin_event_handlers[name])
            del self._plugin_event_handlers[name]

    def update_plugin_events(self: "Anjani") -> None:
        self.update_plugin_event("callback_query", CallbackQueryHandler)
        self.update_plugin_event("chat_action", MessageHandler,
                                 filters=custom_filter.chat_action())
        self.update_plugin_event("inline_query", InlineQueryHandler)
        self.update_plugin_event("message", MessageHandler)

    @property
    def events_activated(self: "Anjani") -> int:
        return len(self._plugin_event_handlers)

    def redact_message(self, text: str) -> str:
        api_id: str = str(self.config["api_id"])
        api_hash: str = self.config["api_hash"]

        if api_id in text:
            text = text.replace(api_id, "[REDACTED]")
        if api_hash in text:
            text = text.replace(api_hash, "[REDACTED]")

        return text

    # Flexible response function with filtering, truncation, redaction, etc.
    async def respond(
        self: "Anjani",
        msg: Message,
        text: str,
        *,
        redact: bool = True,
        response: Optional[Message] = None,
        **kwargs: Any,
    ) -> Message:
        # Redact sensitive information if enabled and known
        if redact:
            text = self.redact_message(text)

        # Truncate messages longer than Telegram's 4096-character length limit
        text = util.tg.truncate(text)

        if response is not None:
            # Already replied, so just edit the existing reply to reduce spam
            return await response.edit(text=text, **kwargs)

        # Reply since we haven't done so yet
        return await msg.reply(text, **kwargs)