"""Initialize Framework for Anjani"""
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

import aiorun

from .core import Anjani, setup_log

aiorun.logger.disabled = True
log = logging.getLogger("Main")
anjani = Anjani()


def start():
    """Main entry point"""
    setup_log()
    log.info("Loading code...")

    try:
        import uvloop  # pylint: disable=C0415
    except ImportError:
        log.warning("uvloop not installed! Skipping...")
        print(
            "\nuvloop not installed! "
            "bot will work the same, but in a bit slower speed.\n"
            'You may install it by "poetry install -E uvloop" or "pip install uvloop"\n'
        )
    else:
        uvloop.install()

    loop = asyncio.new_event_loop()
    aiorun.run(anjani.begin(loop=loop), loop=loop)
