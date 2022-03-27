"""stickers bot commands"""
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

import os
from typing import ClassVar

import pyrogram
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from PIL import Image
from pyrogram.errors import StickersetInvalid
from pyrogram.raw.functions.messages import GetStickerSet, UploadMedia
from pyrogram.raw.functions.stickers import AddStickerToSet, CreateStickerSet
from pyrogram.raw.types import (
    DocumentAttributeFilename,
    InputDocument,
    InputMediaUploadedDocument,
    InputStickerSetItem,
    InputStickerSetShortName,
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from anjani import command, plugin, util


class Stickers(plugin.Plugin):
    """Plugin init, sticker."""

    name: ClassVar[str] = 'Stickers'
    helpable: ClassVar[bool] = True

    async def _resize(self, media: str, video: bool) -> str:  # pylint: disable=no-self-use
        """Resize the given media to 512x512"""
        if video:
            print(video)
            metadata = extractMetadata(createParser(media))
            width = round(metadata.get('width', 512))
            height = round(metadata.get('height', 512))
            if height == width:
                height, width = 512, 512
            elif height > width:
                height, width = 512, -1
            elif width > height:
                height, width = -1, 512

            resized_video = f'{media}.webm'
            arg = (
                f'ffmpeg -i {media} -ss 00:00:00 -to 00:00:03 -map 0:v -b 256k -fs 262144'
                + f' -c:v libvpx-vp9 -vf scale={width}:{height},fps=30 {resized_video} -y'
            )
            await util.system.run_command(arg, shell=True)
            os.remove(media)
            return resized_video

        image = Image.open(media)
        maxsize = 512
        scale = maxsize / max(image.width, image.height)
        new_size = (int(image.width * scale), int(image.height * scale))
        image = image.resize(new_size, Image.LANCZOS)
        resized_photo = 'sticker.png'
        image.save(resized_photo, 'PNG')
        os.remove(media)
        return resized_photo

    async def create_pack(
        self, pack_name: str, short_name: str, sticker: str, emoji: str, set_type: str
    ) -> bool:
        """Sticker pack creator, Return: True if success."""
        media = (
            await self.bot.client.send(
                UploadMedia(
                    peer=await self.bot.client.resolve_peer('stickers'),
                    media=InputMediaUploadedDocument(
                        mime_type=self.bot.client.guess_mime_type(sticker) or 'application/zip',
                        file=(await self.bot.client.save_file(sticker)),
                        force_file=True,
                        thumb=None,
                        attributes=[DocumentAttributeFilename(file_name=os.path.basename(sticker))],
                    ),
                )
            )
        ).document
        await self.bot.client.send(
            CreateStickerSet(
                user_id=await self.bot.client.resolve_peer(self.bot.config['owner_id']),
                title=pack_name,
                short_name=short_name,
                stickers=[
                    InputStickerSetItem(
                        document=InputDocument(
                            id=media.id,
                            access_hash=media.access_hash,
                            file_reference=media.file_reference,
                        ),
                        emoji=emoji,
                    )
                ],
                animated=set_type == 'anim',
                videos=set_type == 'vid',
            )
        )
        return True

    async def add_sticker(self, short_name: str, sticker: str, emoji: str) -> bool:
        """Add file to sticker, Return true if success."""
        media = (
            await self.bot.client.send(
                UploadMedia(
                    peer=await self.bot.client.resolve_peer('stickers'),
                    media=InputMediaUploadedDocument(
                        mime_type=self.bot.client.guess_mime_type(sticker) or 'application/zip',
                        file=(await self.bot.client.save_file(sticker)),
                        force_file=True,
                        thumb=None,
                        attributes=[DocumentAttributeFilename(file_name=os.path.basename(sticker))],
                    ),
                )
            )
        ).document
        await self.bot.client.send(
            AddStickerToSet(
                stickerset=InputStickerSetShortName(short_name=short_name),
                sticker=InputStickerSetItem(
                    document=InputDocument(
                        id=media.id,
                        access_hash=media.access_hash,
                        file_reference=media.file_reference,
                    ),
                    emoji=emoji,
                ),
            )
        )
        return True

    async def cmd_kang(self, ctx: command.Context):
        """Kang sticker handler."""
        chat = ctx.msg.chat
        reply = ctx.msg.reply_to_message
        if not reply or not reply.media:
            return await self.text(chat.id, 'sticker-no-reply')
        setemoji: str = ''
        animset: bool = False
        videoset: bool = False
        resize: bool = False

        await ctx.respond(await self.text(chat.id, 'sticker-kang-process'))
        if reply.photo or reply.document and 'image' in reply.document.mime_type:
            resize: bool = True
        elif reply.animation or (
            reply.document
            and 'video' in reply.document.mime_type
            and reply.document.file_size <= 10485760
        ):
            resize: bool = True
            videoset: bool = True
        elif reply.document and 'tgsticker' in reply.document.mime_type:
            animset: bool = True
        elif reply.sticker:
            if reply.sticker.file_name is None:
                return self.text(chat.id, 'sticker-filename-missing')
            has_emoji = reply.sticker.emoji
            if has_emoji:
                setemoji = has_emoji
            videoset = reply.sticker.is_video
            animset = reply.sticker.is_animated
            if not reply.sticker.file_name.endswith('tgs') or reply.sticker.file_name.endswith(
                '.webm'
            ):
                resize: bool = True
        else:
            return await self.text(chat.id, 'sticker-unsupported-file')
        media = await reply.download()
        if not media:
            return await ctx.text(chat.id, 'sticker-media-notfound')
        args = ctx.args
        packnum: int = 1
        emojiset = None
        if len(args) == 2:
            emojiset, packnum = args
        elif len(args) == 1:
            if ctx.input[0].isnumeric():
                packnum: int = ctx.input[0]
            else:
                emojiset = ctx.input[0]
        if emojiset is not None:
            setas = setemoji
            for k in emojiset:
                if k and k in (
                    getattr(pyrogram.emoji, e) for e in dir(pyrogram.emoji) if not e.startswith('_')
                ):
                    setemoji += k
                if setas and setas != setemoji:
                    setemoji = setemoji[len(setas) :]
        if not setemoji:
            setemoji = '🤔'
        authname = ctx.author.username or ctx.author.id
        packname: str = f'a{ctx.author.id}_Anjani_{packnum}'
        packnick: str = f"{authname}'s Kang Pack Vol.{packnum}"

        if resize:
            media = await self._resize(media, videoset)
        if animset:
            packname += '_anim'
            packnick += ' (Animated)'
        if videoset:
            packname += '_video'
            packnick += ' (Video)'
        hasexist: bool = False
        while True:
            packname += f'_by_{self.bot.user.username}'
            try:
                hasexist = await self.bot.client.send(
                    GetStickerSet(stickerset=InputStickerSetShortName(short_name=packname), hash=0)
                )
            except StickersetInvalid:
                hasexist: bool = False
                break
            else:
                packlimit = 50 if (animset or videoset) else 120
                if hasexist.set.count >= packlimit:
                    packnum += 1
                    packname: str = f'a{ctx.author.id}_Anjani_{packnum}'
                    packnick: str = f"{authname}'s Kang Pack Vol.{packnum}"
                    if animset:
                        packname += '_anim'
                        packnick += ' (Animated)'
                    if videoset:
                        packname += '_video'
                        packnick += ' (Video)'
                    await ctx.respond(
                        await self.text(chat.id, 'sticker-pack-insufficient', packnum)
                    )
                    continue
                break
        if hasexist is not False:
            await self.add_sticker(packname, media, setemoji)
        else:
            set_type = 'anim' if animset else 'vid' if videoset else 'static'
            await self.text(chat.id, 'Sticker-newpack')
            await self.create_pack(packnick, packname, media, setemoji, set_type)
        keyb = InlineKeyboardButton(
            text=await self.text(chat.id, 'sticker-pack-btn'), url=f't.me/addstickers/{packname}'
        )
        await ctx.respond(
            await self.text(chat.id, 'sticker-kang-success'),
            reply_markup=InlineKeyboardMarkup([[keyb]]),
        )
        if os.path.exists(str(media)):
            return os.remove(media)
