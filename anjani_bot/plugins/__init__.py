"""Init file to loads all modules"""
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
from os.path import dirname, basename, isfile
import glob

def __list_all_modules():
    mod_paths = glob.glob(dirname(__file__) + "/*.py")
    return [
        basename(f)[:-3]
        for f in mod_paths
        if isfile(f)
        and f.endswith(".py")
        and not f.endswith("__init  __.py")
    ]


ALL_MODULES = sorted(__list_all_modules())
__all__ = ALL_MODULES + ["ALL_MODULES"]
