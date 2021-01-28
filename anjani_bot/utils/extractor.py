""" text extractor tools """
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

from typing import Optional, Tuple, Union

from pyrogram.types import Message, User


def extract_user_and_text(message: Message) -> Tuple[Union[str, int], Optional[str]]:
    """ extract user and text from message.
    Prioritize user from replied message.
    Returns:
        user (None | int | str) and text (None | str).
    """
    user = None
    text = None
    if message.reply_to_message:
        user = message.reply_to_message.from_user.id
        if message.command:
            text = " ".join(message.command)
        return user, text
    if message.command:
        usr = message.command[0]
        if usr.isdigit():  # user_id
            user = int(usr)
        elif usr.startswith("@"):  # username
            user = usr
        if len(message.command) >= 2:
            text = " ".join(message.command[1:])
        if len(message.command) >= 1 and user is None:
            text = " ".join(message.command)
    return user, text


async def extract_user(client, user_ids: Union[str, int]) -> User:
    """ Excract user from user id """
    return await client.get_users(user_ids)

