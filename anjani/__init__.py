import asyncio
import logging
import os
import sys

import aiorun
import colorlog
from pyrogram.session import Session

from .core import Anjani

Session.notice_displayed = True
aiorun.logger.disabled = True

log = logging.getLogger("launch")


def setup_log() -> None:
    """Configures logging"""
    level = logging.INFO
    logging.root.setLevel(level)

    # Color log config
    log_color: bool = os.environ.get("LOG_COLOR") in {"enable", 1, "1", "true"}

    if log_color:
        formatter = colorlog.ColoredFormatter(
            "  %(log_color)s%(levelname)-7s%(reset)s  |  "
            "%(name)-11s  |  %(log_color)s%(message)s%(reset)s"
        )
    else:
        formatter = logging.Formatter("  %(levelname)-7s  |  %(name)-11s  |  %(message)s")
    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(stream)

    logging.getLogger("pyrogram").setLevel(logging.ERROR)


def start():
    """Main entry point for the bot."""
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
    aiorun.run(Anjani.init_and_run(loop=loop), loop=loop)
