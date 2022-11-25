#!/usr/bin/env python
# Copyright (C) 2020 - 2022  UserbotIndo Team, <https://github.com/userbotindo.git>
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


class Context:
    def __init__(self, message: "Message") -> None:
        self.msg = self.message = message
        self.segments = self.msg.command
        self.invoker = self.segments[0]

    # Lazily resolve expensive fields
    def __getattr__(self, name: str):
        if name == "args":
            return self._get_args()

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    # Argument segments
    def _get_args(self):
        self.args = self.segments[1:]
        return self.args


class Message:
    def __init__(self, text: str = ""):
        self.text = text
        self.command = text[1:].split(" ")
