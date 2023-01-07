"""Anjani database core"""
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

import sys
from typing import TYPE_CHECKING, Any

from anjani import util

from .anjani_mixin_base import MixinBase

if TYPE_CHECKING:
    from .anjani_bot import Anjani


class DatabaseProvider(MixinBase):
    db: util.db.AsyncDatabase

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        if sys.platform == "win32":
            import certifi

            client = util.db.AsyncClient(
                self.config["db_uri"], connect=False, tlsCAFile=certifi.where()
            )
        else:
            client = util.db.AsyncClient(self.config["db_uri"], connect=False)

        self.db = client.get_database("AnjaniBot")

        # Propagate initialization to other mixins
        super().__init__(**kwargs)
