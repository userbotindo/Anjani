"""Anjani database types"""
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

from typing import TypeVar, Union

from pymongo.operations import (
    DeleteMany,
    DeleteOne,
    InsertOne,
    ReplaceOne,
    UpdateMany,
    UpdateOne,
)
from pymongo.read_preferences import (
    Nearest,
    Primary,
    PrimaryPreferred,
    Secondary,
    SecondaryPreferred,
)

ReadPreferences = Union[Primary, PrimaryPreferred, Secondary, SecondaryPreferred, Nearest]
Request = TypeVar("Request", DeleteMany, DeleteOne, InsertOne, ReplaceOne, UpdateMany, UpdateOne)
Results = TypeVar("Results")
