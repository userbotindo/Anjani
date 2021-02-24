"""Bot main starter"""
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
import uvloop

from . import anjani, setup_log

aiorun.logger.disabled = True


def main():
    """Main entry point"""
    log = logging.getLogger("Main")
    setup_log()
    log.info("Loading code...")
    uvloop.install()

    loop = asyncio.new_event_loop()
    aiorun.run(anjani.begin(loop=loop), loop=loop)


if __name__ == "__main__":
    main()
