"""Anjani plugin init"""
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

import importlib
import pkgutil
from pathlib import Path

current_dir = str(Path(__file__).parent)
subplugins = [
    importlib.import_module("." + info.name, __name__)
    for info in pkgutil.iter_modules([current_dir])
]

try:
    _reload_flag: bool

    # noinspection PyUnboundLocalVariable
    if _reload_flag:  # skipcq: PYL-E0601
        # Plugin has been reloaded, reload our subplugins
        for plugin in subplugins:
            importlib.reload(plugin)
except NameError:
    _reload_flag = True
