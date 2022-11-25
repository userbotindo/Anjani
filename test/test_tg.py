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

from anjani.util.tg import parse_button, revert_button, truncate


class TestTgUtils:
    def test_truncate(self):
        text = "Hello World"
        long_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit." * 1000
        assert text == truncate(text)
        assert long_text != truncate(long_text)
        assert truncate(long_text).endswith("... (truncated)")

    def test_parse_button(self):
        text = """Normal text
[Button 1](buttonurl:https://google.com)
[Button 2](buttonurl:youtube.com:same)
[Button 3](buttonurl://reddit.com)"""
        parsed_text, button = parse_button(text)
        assert parsed_text == "Normal text"
        assert button == [
            ("Button 1", "https://google.com", False),
            ("Button 2", "youtube.com", True),
            ("Button 3", "reddit.com", False),
        ]

    def test_revert_button(self):
        button = [
            ("Button 1", "https://google.com", False),
            ("Button 2", "youtube.com", True),
            ("Button 3", "reddit.com", False),
        ]
        reverted_text = revert_button(button)
        assert (
            reverted_text
            == """
[Button 1](buttonurl://https://google.com)
[Button 2](buttonurl://youtube.com:same)
[Button 3](buttonurl://reddit.com)"""
        )

    def test_parse_reverted_button(self):
        text = """
[Button 1](buttonurl://https://google.com)
[Button 2](buttonurl://youtube.com:same)
[Button 3](buttonurl://reddit.com)"""
        parsed_text, button = parse_button(text)
        assert parsed_text == ""
        assert button == [
            ("Button 1", "https://google.com", False),
            ("Button 2", "youtube.com", True),
            ("Button 3", "reddit.com", False),
        ]
