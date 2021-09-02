import asyncio
import logging
import os
import sys
from typing import Any

import aiorun
import colorlog
from dotenv import load_dotenv
from pyrogram.session import Session

from .core import Anjani
from .util.config import TelegramConfig

Session.notice_displayed = True
aiorun.logger.disabled = True

log = logging.getLogger("launch")


def _level_check(level: str) -> int:
    _str_to_lvl = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
    }
    if level not in _str_to_lvl:
        return logging.INFO
    return _str_to_lvl[level]


def setup_log() -> None:
    """Configures logging"""
    level = _level_check(os.environ.get("LOG_LEVEL", "info").upper())
    logging.root.setLevel(level)

    # Color log config
    log_color: bool = os.environ.get("LOG_COLOR") in {"enable", 1, "1", "true"}

    file_format = "[ %(asctime)s: %(levelname)-8s ] %(name)-15s - %(message)s"
    logfile = logging.FileHandler("Anjani.log")
    formatter = logging.Formatter(file_format, datefmt="%H:%M:%S")
    logfile.setFormatter(formatter)
    logfile.setLevel(level)

    if log_color:
        formatter = colorlog.ColoredFormatter(
            "  %(log_color)s%(levelname)-8s%(reset)s  |  "
            "%(name)-11s  |  %(log_color)s%(message)s%(reset)s"
        )
    else:
        formatter = logging.Formatter("  %(levelname)-8s  |  %(name)-11s  |  %(message)s")
    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(stream)
    root.addHandler(logfile)

    logging.getLogger("pyrogram").setLevel(logging.ERROR)


def start() -> None:
    """Main entry point for the bot."""
    if os.path.isfile("config.env"):
        load_dotenv("config.env")

    setup_log()
    log.info("Loading code")

    if sys.platform == "win32":
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
    else:
        try:
            import uvloop
        except ImportError:
            pass
        else:
            uvloop.install()
            log.info("Using uvloop event loop")

    log.info("Initializing bot")
    loop = asyncio.new_event_loop()

    # Check mandatory configuration
    config: TelegramConfig[str, Any] = TelegramConfig()
    if any(key not in config for key in {"api_id", "api_hash", "bot_token", "db_uri"}):
        return log.error("Configuration must be done correctly before running the bot.")

    aiorun.run(Anjani.init_and_run(config, loop=loop), loop=loop)
