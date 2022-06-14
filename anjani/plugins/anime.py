""" Anime Plugin """
from datetime import datetime
from typing import Any, ClassVar, Mapping, MutableMapping, Optional

from aiopath import AsyncPath
from pyrogram.errors import WebpageMediaEmpty
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
)

from anjani import command, filters, listener, plugin

MESSAGE_CHAR_LIMIT = 1024
TRUNCATION_SUFFIX = "...<i><a href='{link}'>READ MORE</a></i>"


def truncate(text: str, link: str) -> str:
    """Truncates the given text to fit in one Telegram message with read more link."""

    if len(text) > MESSAGE_CHAR_LIMIT:
        return text[: MESSAGE_CHAR_LIMIT - len(TRUNCATION_SUFFIX)] + TRUNCATION_SUFFIX.format(
            link=link
        )

    return text


name_query = """
query ($page: Int, $perPage: Int, $search: String, $id: Int) {
    Page(page: $page, perPage: $perPage) {
        pageInfo {
            total
            perPage
            currentPage
            lastPage
            hasNextPage
        }
        media(id: $id, search: $search, type: ANIME) {
            id
            episodes
            title {
                romaji
                english
                native
            }
            averageScore
            type
            genres
            duration
            startDate {
              year
              month
              day
            }
            endDate {
              year
              month
              day
            }
            status
            nextAiringEpisode {
                airingAt
                timeUntilAiring
                episode
            }
            studios(sort: NAME_DESC) {
              nodes {
                name
                siteUrl
              }
            }
            siteUrl
            description(asHtml: true)
        }
    }
}
"""
trending_query = """
query ($page: Int, $perPage: Int) {
    Page(page: $page, perPage: $perPage) {
        pageInfo {
            total
            perPage
            currentPage
            lastPage
            hasNextPage
        }
        media(type: ANIME, sort: TRENDING_DESC) {
            id
            episodes
            title {
                romaji
                english
                native
            }
            averageScore
            type
            genres
            duration
            startDate {
              year
              month
              day
            }
            endDate {
              year
              month
              day
            }
            status
            nextAiringEpisode {
                airingAt
                timeUntilAiring
                episode
            }
            studios(sort: NAME_DESC) {
              nodes {
                name
                siteUrl
              }
            }
            siteUrl
            description(asHtml: true)
        }
    }
}
"""
airing_query = """
query ($page: Int, $perPage: Int) {
    Page(page: $page, perPage: $perPage) {
        pageInfo {
            total
            perPage
            currentPage
            lastPage
            hasNextPage
        }
        media(type: ANIME, status: RELEASING, sort: POPULARITY_DESC) {
            id
            episodes
            title {
                romaji
                english
                native
            }
            averageScore
            type
            genres
            duration
            startDate {
              year
              month
              day
            }
            endDate {
              year
              month
              day
            }
            status
            nextAiringEpisode {
                airingAt
                timeUntilAiring
                episode
            }
            studios(sort: NAME_DESC) {
              nodes {
                name
                siteUrl
              }
            }
            siteUrl
            description(asHtml: true)
        }
    }
}
"""
upcoming_query = """
query ($page: Int, $perPage: Int) {
    Page(page: $page, perPage: $perPage) {
        pageInfo {
            total
            perPage
            currentPage
            lastPage
            hasNextPage
        }
        media(type: ANIME, status: NOT_YET_RELEASED, sort: POPULARITY_DESC) {
            id
            episodes
            title {
                romaji
                english
                native
            }
            averageScore
            type
            genres
            duration
            startDate {
              year
              month
              day
            }
            endDate {
              year
              month
              day
            }
            status
            nextAiringEpisode {
                airingAt
                timeUntilAiring
                episode
            }
            studios(sort: NAME_DESC) {
              nodes {
                name
                siteUrl
              }
            }
            siteUrl
            description(asHtml: true)
        }
    }
}
"""


class Anime(plugin.Plugin):
    """
    Anime plugin for Anjani.
    """

    name: ClassVar[str] = "Anime"
    # TO-DO: add helpable
    helpable: ClassVar[bool] = False

    move_map: MutableMapping[str, int]

    async def on_load(self) -> None:
        # Declare here so we don't declare everytime the button gets called
        self.move_map = {"prev": -1, "next": 1}

    @listener.filters(
        filters.regex(
            r"^anilist_(?P<category>airing|search\((?P<name>[\S\s]+)\)|trending|upcoming)_"
            r"page\((?P<current_page>\d+)\)_"
            r"action\((?P<move>prev|next)\)$"
        )
    )
    async def on_callback_query(self, query: CallbackQuery) -> None:
        page_data = query.matches[0].groupdict()
        move = page_data["move"]
        current_page = int(page_data["current_page"])

        data: Mapping[str, Any]
        if page_data["name"] is not None:
            data = await self.search(page_data["name"], current_page + self.move_map[move])
        else:
            data = await self.__getattribute__(page_data["category"])(
                current_page + self.move_map[move]
            )

        try:
            await query.message.edit_media(
                InputMediaPhoto(data["coverImage"], caption=data["metadata"]),
                reply_markup=InlineKeyboardMarkup(data["button"]),
            )
        except WebpageMediaEmpty:
            async with self.bot.http.get(data["coverImage"]) as resp:
                cover = AsyncPath(f"downloads/{data['coverImage'].split('/')[-1] + '.png'}")
                content = await resp.read()

            await cover.write_bytes(content)
            await query.message.edit_media(
                InputMediaPhoto(str(cover), caption=data["metadata"]),
                reply_markup=InlineKeyboardMarkup(data["button"]),
            )
            await cover.unlink()
        await query.answer()

    # TO-DO
    async def extract_metadata(
        self, name: str, data: Mapping[str, Any]
    ) -> MutableMapping[str, Any]:
        return {}

    async def get(self, query: str, variables: MutableMapping[str, Any]) -> Mapping[str, Any]:
        try:
            async with self.bot.http.post(
                "https://graphql.anilist.co", json={"query": query, "variables": variables}
            ) as resp:
                return await resp.json()
        except Exception:
            return {}

    async def airing(self, page: int = 1) -> Mapping[str, Any]:
        """
        Get airing anime on Anilist.
        """
        data = await self.get(airing_query, {"page": page, "perPage": 1})
        metadata = ""
        page_info = data["data"]["Page"]["pageInfo"]
        for anime in data["data"]["Page"]["media"]:
            metadata += f"<a href='{anime['siteUrl']}'>{anime['title']['romaji']} ({anime['title']['native']})</a>\n\n"
            metadata += f"<b>Status</b>: {anime['status']}\n"
            metadata += (
                f"<b>Episodes</b>: {'N/A' if anime['episodes'] is None else anime['episodes']}\n"
            )
            if anime["status"] == "RELEASING":
                metadata += f"<b>Current Episode</b>: {anime['nextAiringEpisode']['episode'] if anime['nextAiringEpisode'] is not None else 'N/A'}\n"
                metadata += f"<b>Next Airing At</b>: {datetime.fromtimestamp(anime['nextAiringEpisode']['airingAt']).strftime('%Y-%m-%d %H:%M:%S') if anime['nextAiringEpisode'] is not None else 'N/A'}\n"
            metadata += f"<b>Duration</b>: {'N/A' if anime['duration'] is None else str(anime['duration']) + ' minutes'}{'/ep' if anime['type'] != 'MOVIE' and anime['duration'] is not None else ''}\n"
            metadata += f"<b>Score</b>: {'N/A' if anime['averageScore'] is None else '⭐️ ' + str(anime['averageScore'])}\n"
            metadata += f"<b>Genres</b>: {', '.join(['<code>' + genre + '</code>' for genre in anime['genres']]) if anime['genres'] else 'N/A'}\n"
            metadata += f"<b>Studios</b>: {', '.join(['<code>' + studio['name'] + '</code>' for studio in anime['studios']['nodes']]) if anime['studios']['nodes'] else 'N/A'}\n"
            metadata += f"<b>Description</b>: {anime['description']}"
            metadata = truncate(metadata, anime["siteUrl"])

            button = []
            current_page = page_info["currentPage"]
            if current_page > 1:
                button.append(
                    [
                        InlineKeyboardButton(
                            "⏪ Previous",
                            callback_data=f"anilist_airing_page({current_page})_action(prev)",
                        )
                    ]
                )
            if current_page < page_info["lastPage"]:
                if current_page == 1:
                    button.append(
                        [
                            InlineKeyboardButton(
                                "Next ⏩",
                                callback_data=f"anilist_airing_page({current_page})_action(next)",
                            )
                        ]
                    )
                else:
                    button[0].append(
                        InlineKeyboardButton(
                            "Next ⏩",
                            callback_data=f"anilist_airing_page({current_page})_action(next)",
                        )
                    )

            return {
                "metadata": metadata,
                "coverImage": f"https://img.anili.st/media/{anime['id']}",
                "button": button,
            }

        raise ValueError("Something went wrong.")

    async def search(self, name: str, page: int = 1) -> Mapping[str, Any]:
        """
        Search anime.
        """
        data = await self.get(name_query, {"search": name, "page": page, "perPage": 1})
        metadata = ""
        page_info = data["data"]["Page"]["pageInfo"]

        # Get next data for proper button
        next_data = await self.get(name_query, {"search": name, "page": page + 1, "perPage": 1})
        total = next_data["data"]["Page"]["pageInfo"]["total"]

        button = []
        current_page = page_info["currentPage"]
        if current_page > 1:
            button.append(
                [
                    InlineKeyboardButton(
                        "⏪ Previous",
                        callback_data=f"anilist_search({name})_page({current_page})_action(prev)",
                    )
                ]
            )
        if page_info["hasNextPage"]:
            if current_page == 1:
                button.append(
                    [
                        InlineKeyboardButton(
                            "Next ⏩",
                            callback_data=f"anilist_search({name})_page({current_page})_action(next)",
                        )
                    ]
                )
            else:
                if current_page < total:
                    button[0].append(
                        InlineKeyboardButton(
                            "Next ⏩",
                            callback_data=f"anilist_search({name})_page({current_page})_action(next)",
                        )
                    )

        for anime in data["data"]["Page"]["media"]:
            metadata += f"<a href='{anime['siteUrl']}'>{anime['title']['romaji']} ({anime['title']['native']})</a>\n\n"
            metadata += f"<b>Status</b>: {anime['status']}\n"
            metadata += (
                f"<b>Episodes</b>: {'N/A' if anime['episodes'] is None else anime['episodes']}\n"
            )
            if anime["status"] == "RELEASING":
                metadata += f"<b>Current Episode</b>: {anime['nextAiringEpisode']['episode'] if anime['nextAiringEpisode'] is not None else 'N/A'}\n"
                metadata += f"<b>Next Airing At</b>: {datetime.fromtimestamp(anime['nextAiringEpisode']['airingAt']).strftime('%Y-%m-%d %H:%M:%S') if anime['nextAiringEpisode'] is not None else 'N/A'}\n"
            metadata += f"<b>Duration</b>: {'N/A' if anime['duration'] is None else str(anime['duration']) + ' minutes'}{'/ep' if anime['type'] != 'MOVIE' and anime['duration'] is not None else ''}\n"
            metadata += f"<b>Score</b>: {'N/A' if anime['averageScore'] is None else '⭐️ ' + str(anime['averageScore'])}\n"
            metadata += f"<b>Genres</b>: {', '.join(['<code>' + genre + '</code>' for genre in anime['genres']]) if anime['genres'] else 'N/A'}\n"
            metadata += f"<b>Studios</b>: {', '.join(['<code>' + studio['name'] + '</code>' for studio in anime['studios']['nodes']]) if anime['studios']['nodes'] else 'N/A'}\n"
            metadata += f"<b>Description</b>: {anime['description']}"
            metadata = truncate(metadata, anime["siteUrl"])

            return {
                "metadata": metadata,
                "coverImage": f"https://img.anili.st/media/{anime['id']}",
                "button": button,
            }

        raise IndexError

    async def trending(self, page: int = 1) -> Mapping[str, Any]:
        """
        Return trending anime.
        """
        data = await self.get(trending_query, {"page": page, "perPage": 1})
        metadata = ""
        page_info = data["data"]["Page"]["pageInfo"]
        for anime in data["data"]["Page"]["media"]:
            metadata += f"<a href='{anime['siteUrl']}'>{anime['title']['romaji']} ({anime['title']['native']})</a>\n\n"
            metadata += f"<b>Status</b>: {anime['status']}\n"
            metadata += (
                f"<b>Episodes</b>: {'N/A' if anime['episodes'] is None else anime['episodes']}\n"
            )
            if anime["status"] == "RELEASING":
                metadata += f"<b>Current Episode</b>: {anime['nextAiringEpisode']['episode'] if anime['nextAiringEpisode'] is not None else 'N/A'}\n"
                metadata += f"<b>Next Airing At</b>: {datetime.fromtimestamp(anime['nextAiringEpisode']['airingAt']).strftime('%Y-%m-%d %H:%M:%S') if anime['nextAiringEpisode'] is not None else 'N/A'}\n"
            metadata += f"<b>Duration</b>: {'N/A' if anime['duration'] is None else str(anime['duration']) + ' minutes'}{'/ep' if anime['type'] != 'MOVIE' and anime['duration'] is not None else ''}\n"
            metadata += f"<b>Score</b>: {'N/A' if anime['averageScore'] is None else '⭐️ ' + str(anime['averageScore'])}\n"
            metadata += f"<b>Genres</b>: {', '.join(['<code>' + genre + '</code>' for genre in anime['genres']]) if anime['genres'] else 'N/A'}\n"
            metadata += f"<b>Studios</b>: {', '.join(['<code>' + studio['name'] + '</code>' for studio in anime['studios']['nodes']]) if anime['studios']['nodes'] else 'N/A'}\n"
            metadata += f"<b>Description</b>: {anime['description']}"
            metadata = truncate(metadata, anime["siteUrl"])

            button = []
            current_page = page_info["currentPage"]
            if current_page > 1:
                button.append(
                    [
                        InlineKeyboardButton(
                            "⏪ Previous",
                            callback_data=f"anilist_trending_page({current_page})_action(prev)",
                        )
                    ]
                )
            if current_page < page_info["lastPage"]:
                if current_page == 1:
                    button.append(
                        [
                            InlineKeyboardButton(
                                "Next ⏩",
                                callback_data=f"anilist_trending_page({current_page})_action(next)",
                            )
                        ]
                    )
                else:
                    button[0].append(
                        InlineKeyboardButton(
                            "Next ⏩",
                            callback_data=f"anilist_trending_page({current_page})_action(next)",
                        )
                    )

            return {
                "metadata": metadata,
                "coverImage": f"http://img.anili.st/media/{anime['id']}",
                "button": button,
            }

        raise ValueError("Something went wrong.")

    async def upcoming(self, page: int = 1) -> Mapping[str, Any]:
        """
        Get upcoming anime on Anilist.
        """
        data = await self.get(upcoming_query, {"page": page, "perPage": 1})
        metadata = ""
        page_info = data["data"]["Page"]["pageInfo"]
        for anime in data["data"]["Page"]["media"]:
            metadata += f"<a href='{anime['siteUrl']}'>{anime['title']['romaji']} ({anime['title']['native']})</a>\n\n"
            if anime["nextAiringEpisode"] is not None:
                metadata += f"<b>Start Airing At</b>: {datetime.fromtimestamp(anime['nextAiringEpisode']['airingAt']).strftime('%Y-%m-%d %H:%M:%S')}\n"
            else:
                metadata += f"<b>Start Airing At</b>: TBA\n"
            metadata += f"<b>Genres</b>: {', '.join(['<code>' + genre + '</code>' for genre in anime['genres']]) if anime['genres'] else 'N/A'}\n"
            metadata += f"<b>Studios</b>: {', '.join(['<code>' + studio['name'] + '</code>' for studio in anime['studios']['nodes']]) if anime['studios']['nodes'] else 'N/A'}\n"
            metadata += f"<b>Description</b>: {anime['description']}"
            metadata = truncate(metadata, anime["siteUrl"])

            button = []
            current_page = page_info["currentPage"]
            if current_page > 1:
                button.append(
                    [
                        InlineKeyboardButton(
                            "⏪ Previous",
                            callback_data=f"anilist_upcoming_page({current_page})_action(prev)",
                        )
                    ]
                )
            if current_page < page_info["lastPage"]:
                if current_page == 1:
                    button.append(
                        [
                            InlineKeyboardButton(
                                "Next ⏩",
                                callback_data=f"anilist_upcoming_page({current_page})_action(next)",
                            )
                        ]
                    )
                else:
                    button[0].append(
                        InlineKeyboardButton(
                            "Next ⏩",
                            callback_data=f"anilist_upcoming_page({current_page})_action(next)",
                        )
                    )

            return {
                "metadata": metadata,
                "coverImage": f"https://img.anili.st/media/{anime['id']}",
                "button": button,
            }

        raise ValueError("Something went wrong.")

    async def cmd_anilist(self, ctx: command.Context) -> Optional[str]:
        """
        Search anime on Anilist.
        """
        name = ctx.input
        if not name:
            return "Please specify category or name."

        data: Mapping[str, Any]
        if name in {"airing", "trending", "upcoming"}:
            data = await self.__getattribute__(name)()
        else:
            data = await self.search(name)

        try:
            await ctx.respond(
                data["metadata"],
                photo=data["coverImage"],
                reply_markup=InlineKeyboardMarkup(data["button"]) if data["button"] else None,
                reply_to_message_id=ctx.message.id,
            )
        except WebpageMediaEmpty:
            async with self.bot.http.get(data["coverImage"]) as resp:
                cover = AsyncPath(f"downloads/{data['coverImage'].split('/')[-1] + '.png'}")
                content = await resp.read()

            await cover.write_bytes(content)
            await ctx.respond(
                data["metadata"],
                photo=str(cover),
                reply_markup=InlineKeyboardMarkup(data["button"]) if data["button"] else None,
                reply_to_message_id=ctx.message.id,
            )
            await cover.unlink()
