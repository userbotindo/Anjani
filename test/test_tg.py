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
        long_text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec libero tellus, tempor at tincidunt ut, convallis vel dolor. Fusce tincidunt ligula ut diam maximus, tincidunt posuere magna pulvinar. Ut tincidunt semper sapien, vel ultrices lectus blandit quis. Fusce non eros at sem pretium luctus. Praesent ut mi non augue rutrum facilisis. Suspendisse erat arcu, sagittis quis condimentum id, tincidunt ut ex. Aenean quis mauris in nunc porta consectetur id id libero. Aliquam pharetra a arcu porta posuere. Proin accumsan neque vel neque molestie fringilla. Nam purus tellus, vestibulum id aliquam at, efficitur in tellus.

Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Sed massa urna, dignissim et orci eget, lobortis mattis nibh. Curabitur quis commodo nulla. Sed varius vel nunc id convallis. Ut nec laoreet mauris, a lacinia tellus. Donec mattis felis ac dui fermentum, non lobortis dolor fringilla. Suspendisse et enim purus. Vestibulum augue augue, volutpat quis mi quis, mattis porta ligula. In hac habitasse platea dictumst. Mauris sagittis vehicula nisl, et euismod justo. Pellentesque purus sapien, ornare ut condimentum vel, interdum vitae ipsum.

In felis erat, dictum eu pulvinar ut, elementum vitae augue. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Sed feugiat condimentum cursus. Aenean ac dictum lacus, ut efficitur mi. Praesent consectetur et nisi vitae bibendum. Integer sem purus, rutrum sit amet imperdiet a, venenatis ut neque. Ut porta ante mi, at ullamcorper nisl consectetur sit amet. Maecenas mollis, sem quis ornare aliquet, sem metus laoreet urna, quis efficitur ante dolor sed massa. Sed tempus, nisl et tempor mollis, leo ex viverra nibh, malesuada ornare nisi nibh in augue. Aliquam id ex egestas nulla semper lobortis ut at diam. Etiam cursus facilisis lacus a volutpat.

Morbi sodales suscipit enim, nec iaculis libero. Mauris rhoncus, mi sit amet porttitor varius, urna magna placerat eros, nec blandit arcu arcu ut nisi. Aliquam viverra purus id nisi accumsan, quis bibendum massa convallis. Cras sed dolor sit amet diam tincidunt suscipit quis ut elit. Ut turpis odio, pulvinar vel placerat malesuada, semper id dolor. Sed vitae leo quis tellus aliquam convallis. Vestibulum vulputate, velit nec consequat iaculis, metus nibh varius orci, sit amet semper turpis dolor vitae lorem. Curabitur sit amet augue dui. Ut sit amet lectus diam. Nam id ligula ut ipsum volutpat lobortis. Donec tristique, felis id dignissim vestibulum, massa enim pretium arcu, sit amet tincidunt turpis erat in metus. Vivamus ac fermentum nibh. Donec eget interdum lacus, id scelerisque elit. Nullam luctus pellentesque libero, sed placerat magna congue sit amet. Praesent suscipit hendrerit faucibus. Morbi molestie vehicula eleifend.

Vivamus cursus lobortis mauris, vel aliquam odio congue eu. Praesent neque lacus, varius sed tortor in, tristique elementum tellus. Praesent nisl libero, tempor id sollicitudin rutrum, feugiat a ante. Morbi et ligula consequat, sagittis leo sit amet, gravida libero. Proin molestie ut turpis ac vehicula. Cras faucibus orci et mi viverra consequat. Curabitur neque nisi, placerat ut nisl quis, lacinia lacinia ante. Donec viverra tortor massa, eu tristique ex ultrices id. Nulla lacinia ex non nunc tristique aliquam. Phasellus varius euismod diam non congue.

Donec ac lorem in felis congue consequat id vitae sapien. Donec ut erat dapibus mauris condimentum convallis. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Donec fermentum porttitor metus, a hendrerit turpis varius viverra. Phasellus quis mauris sed nisi efficitur pellentesque sed id leo. Proin eu arcu ut enim tempus sodales et at dolor. Fusce nec porta metus.

Pellentesque nisl mauris, luctus eget accumsan eu, consectetur quis lectus. Aliquam commodo purus eu urna porta tristique. Fusce volutpat lacinia augue, id lobortis nisl ultricies ac. Sed euismod eros eu lectus commodo, eget vehicula lacus efficitur. Ut efficitur, augue nec laoreet varius, mauris risus suscipit felis, ac accumsan ac."""
        assert text == truncate(text)
        assert long_text != truncate(long_text)
        assert truncate(long_text).endswith("... (truncated)")

    def test_parse_button(self):
        text = """Normal text
[Button 1](buttonurl:https//google.com)
[Button 2](buttonurl:youtube.com:same)
[Button 3](buttonurl://reddit.com)"""
        parsed_text, button = parse_button(text)
        assert parsed_text == "Normal text"
        assert button == [
            ("Button 1", "https//google.com", False),
            ("Button 2", "youtube.com", True),
            ("Button 3", "reddit.com", False),
        ]

    def test_revert_button(self):
        button = [
            ("Button 1", "https//google.com", False),
            ("Button 2", "youtube.com", True),
            ("Button 3", "reddit.com", False),
        ]
        reverted_text = revert_button(button)
        print(reverted_text)
        assert (
            reverted_text
            == """
[Button 1](buttonurl://https//google.com)
[Button 2](buttonurl://youtube.com:same)
[Button 3](buttonurl://reddit.com)"""
        )
