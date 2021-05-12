"""Bot Plugins loader"""
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

import inspect
import logging
from types import ModuleType
from typing import TYPE_CHECKING, Any, Iterable, List, MutableMapping, Optional, Type

from pyrogram.types import InlineKeyboardButton

from .. import plugin
from .base import Base  # pylint: disable=R0401

if TYPE_CHECKING:
    from .anjani import Anjani

LOGGER = logging.getLogger(__name__)


class PluginExtender(Base):
    """Core plugin.Plugin Initialization"""

    plugins: MutableMapping[str, plugin.Plugin]

    def __init__(self: "Anjani", **kwargs: Any) -> None:
        self.plugins = {}

        super().__init__(**kwargs)

    def load_plugin(self, cls: Type[plugin.Plugin], *, comment: Optional[str] = None) -> None:
        """Load bot plugin"""
        LOGGER.debug(f"Loading {cls.format_desc(comment)}")

        ext = cls(self)
        ext.comment = comment
        self.plugins[cls.name] = ext

        # load database
        if hasattr(ext, "__on_load__"):
            self.loop.create_task(ext.__on_load__())
            LOGGER.debug(f"Database plugin '{cls.name}' loaded.")

    def unload_plugin(self, ext: plugin.Plugin) -> None:
        """Unload bot plugin"""
        cls = type(ext)
        LOGGER.info(f"Unloading {ext.format_desc(ext.comment)}")

        del self.plugins[cls.name]

    def _load_all_from_metaplugin(
        self, subplugins: Iterable[ModuleType], *, comment: str = None
    ) -> None:
        for extension in subplugins:
            for sym in dir(extension):
                cls = getattr(extension, sym)
                if inspect.isclass(cls) and issubclass(cls, plugin.Plugin) and not cls.disabled:
                    self.load_plugin(cls, comment=comment)

    # noinspection PyTypeChecker,PyTypeChecker
    def load_all_plugins(self, subplugins: Iterable[ModuleType]) -> None:
        """Load available plugin"""
        LOGGER.info("Loading plugins")
        self._load_all_from_metaplugin(subplugins)
        self.plugins = dict(sorted(self.plugins.items()))
        LOGGER.info(f"Plugins loaded {list(self.plugins.keys())}")

    def unload_all_plugins(self) -> None:
        """Unload plugins"""
        LOGGER.info("Unloading plugins...")
        # Can't modify while iterating, so collect a list first
        for ext in list(self.plugins.values()):
            self.unload_plugin(ext)

        LOGGER.info("All plugins unloaded.")

    async def help_builder(self, chat_id: int) -> List:
        """Build the help button"""
        plugins: List[InlineKeyboardButton] = []
        for cls in list(self.plugins.values()):
            if hasattr(cls, "helpable") and cls.helpable is True:
                plugins.append(
                    InlineKeyboardButton(
                        await self.text(chat_id, f"{cls.name.lower()}-button"),
                        callback_data="help_plugin({})".format(cls.name.lower()),
                    )
                )

        pairs = [plugins[i * 3 : (i + 1) * 3] for i in range((len(plugins) + 3 - 1) // 3)]
        return pairs
