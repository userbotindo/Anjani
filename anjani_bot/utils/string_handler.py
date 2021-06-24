"""Message types handler"""
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

import re
from enum import IntEnum, unique
from typing import List, Union

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


@unique
class Types(IntEnum):
    TEXT = 0
    BUTTON_TEXT = 1
    DOCUMENT = 2
    PHOTO = 3
    VIDEO = 4
    STICKER = 5
    AUDIO = 6
    VOICE = 7
    VIDEO_NOTE = 8
    ANIMATION = 9


class SendFormating:
    """A message sending method mapper based on message type"""

    bot: "~Anjani"

    def __init__(self):
        self.send_format = {
            Types.TEXT.value: self.bot.client.send_message,
            Types.BUTTON_TEXT.value: self.bot.client.send_message,
            Types.DOCUMENT.value: self.bot.client.send_document,
            Types.PHOTO.value: self.bot.client.send_photo,
            Types.VIDEO.value: self.bot.client.send_video,
            Types.STICKER.value: self.bot.client.send_sticker,
            Types.AUDIO.value: self.bot.client.send_audio,
            Types.VOICE.value: self.bot.client.send_voice,
            Types.VIDEO_NOTE.value: self.bot.client.send_video_note,
            Types.ANIMATION.value: self.bot.client.send_animation,
        }


class MessageParser:
    @staticmethod
    def build_button(buttons: List) -> Union[InlineKeyboardMarkup, None]:
        """Build saved button format"""
        if not buttons:
            return None
        keyb = []
        for btn in buttons:
            if btn[2] and keyb:
                keyb[-1].append(InlineKeyboardButton(btn[0], url=btn[1]))
            else:
                keyb.append([InlineKeyboardButton(btn[0], url=btn[1])])
        return InlineKeyboardMarkup(keyb)

    @staticmethod
    def revert_button(button: List) -> str:
        """Revert button format"""
        res = ""
        for btn in button:
            if btn[2]:
                res += f"\n[{btn[0]}](buttonurl://{btn[1]}:same)"
            else:
                res += f"\n[{btn[0]}](buttonurl://{btn[1]})"
        return res

    @staticmethod
    def parse_button(text):
        """Parse button to save"""
        btn_regex = re.compile(r"(\[([^\[]+?)\]\(buttonurl:(?:/{0,2})(.+?)(:same)?\))")

        prev = 0
        parser_data = ""
        buttons = []
        if not text:
            return "", buttons
        for match in btn_regex.finditer(text):
            # escape check
            md_escaped = 0
            to_check = match.start(1) - 1
            while to_check > 0 and text[to_check] == "\\":
                md_escaped += 1
                to_check -= 1

            # if != "escaped" -> Create button: btn
            if md_escaped % 2 == 0:
                # create a thruple with button label, url, and newline status
                buttons.append((match.group(2), match.group(3), bool(match.group(4))))
                parser_data += text[prev : match.start(1)]
                prev = match.end(1)
            # if odd, escaped -> move along
            else:
                parser_data += text[prev:to_check]
                prev = match.start(1) - 1

        parser_data += text[prev:]

        return parser_data.rstrip(), buttons

    def get_msg_type(self, msg: Message):
        """Parse recieved message and return all its content"""
        msg_type = None
        msg_content = None
        msg_text = ""
        buttons = []

        if not msg.reply_to_message:
            args = msg.text.markdown.split(" ", 2)
            msg_text, buttons = self.parse_button(args[2])
            msg_type = Types.BUTTON_TEXT if buttons else Types.TEXT
        elif msg.reply_to_message:
            text = msg.reply_to_message.text or msg.reply_to_message.caption
            if text:
                msg_text, buttons = self.parse_button(text.markdown)
            if msg.reply_to_message.text:
                msg_type = Types.BUTTON_TEXT if buttons else Types.TEXT
            elif msg.reply_to_message.sticker:
                msg_content = msg.reply_to_message.sticker.file_id
                msg_type = Types.STICKER
            elif msg.reply_to_message.document:
                msg_content = msg.reply_to_message.document.file_id
                msg_type = Types.DOCUMENT
            elif msg.reply_to_message.photo:
                msg_content = msg.reply_to_message.photo.file_id
                msg_type = Types.PHOTO
            elif msg.reply_to_message.audio:
                msg_content = msg.reply_to_message.audio.file_id
                msg_type = Types.AUDIO
            elif msg.reply_to_message.voice:
                msg_content = msg.reply_to_message.voice.file_id
                msg_type = Types.VOICE
            elif msg.reply_to_message.video:
                msg_content = msg.reply_to_message.video.file_id
                msg_type = Types.VIDEO
        return msg_text, msg_type, msg_content, buttons
