"""Admin check utils"""
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


async def adminlist(client, chat_id):
    """This Function to get admin list."""
    admins = []
    async for i in client.iter_chat_members(chat_id):
        if i.status in ["administrator", "creator"]:
            admins.append(i.user.id)
    return admins
