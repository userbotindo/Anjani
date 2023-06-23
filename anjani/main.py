"""Anjani main entry point"""
# Copyright (C) 2020 - 2023  UserbotIndo Team, <https://github.com/userbotindo.git>
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
import sys
from pathlib import Path
from typing import Any, MutableMapping

import aiorun
import colorlog
import dotenv

from . import DEFAULT_CONFIG_PATH
from .core import Anjani
from .util.config import Config

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


def _setup_log() -> None:
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
            "%(name)-15s  |  %(log_color)s%(message)s%(reset)s"
        )
    else:
        formatter = logging.Formatter("  %(levelname)-8s  |  %(name)-15s  |  %(message)s")
    stream = logging.StreamHandler()
    stream.setLevel(level)
    stream.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(stream)
    root.addHandler(logfile)

    # Logging necessary for selected libs
    aiorun.logger.disabled = True
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("pyrogram").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def start() -> None:
    """Main entry point for the bot."""
    config_path = Path(DEFAULT_CONFIG_PATH)
    if config_path.is_file():
        dotenv.load_dotenv(config_path)

    _setup_log()
    log.info(
        "Running on Python %s.%s.%s",
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )
    log.info("Loading code")

    _uvloop = False
    if sys.platform == "win32":
        policy = asyncio.WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
    else:
        try:
            import uvloop  # type: ignore
        except ImportError:
            pass
        else:
            uvloop.install()
            _uvloop = True
            log.info("Using uvloop event loop")

    log.info("Initializing bot")
    loop = asyncio.new_event_loop()

    aiorun.run(Anjani.init_and_run(Config(), loop=loop), loop=loop if _uvloop else None)
