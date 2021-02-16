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
from typing import Any, Iterable, MutableMapping, Optional, Type, List

from pyrogram.types import InlineKeyboardButton

from .. import plugin

LOGGER = logging.getLogger(__name__)


class PluginExtender:
    modules: MutableMapping[str, plugin.Plugin]
    helpable = list()
    __migrateable = list()

    def __init__(self, **kwargs: Any) -> None:
        self.modules = {}

        super().__init__(**kwargs)

    def load_module(
            self, cls: Type[plugin.Plugin], *, comment: Optional[str] = None
        ) -> None:
        """ Load bot module"""
        LOGGER.debug("Loading %s", cls.format_desc(comment))

        mod = cls(self)
        mod.comment = comment
        self.modules[cls.name] = mod
        if hasattr(mod, "__migrate__"):
            self.__migrateable.append(mod)
        if hasattr(mod, "helpable"):
            self.helpable.append(mod)

    def unload_module(self, mod: plugin.Plugin) -> None:
        """ Unload bot module """
        cls = type(mod)
        LOGGER.info("Unloading %s", mod.format_desc(mod.comment))

        del self.modules[cls.name]

    def _load_all_from_metamod(
            self, submodules: Iterable[ModuleType], *, comment: str = None
        ) -> None:
        for module_mod in submodules:
            for sym in dir(module_mod):
                cls = getattr(module_mod, sym)
                if (
                        inspect.isclass(cls)
                        and issubclass(cls, plugin.Plugin)
                        and not cls.disabled
                    ):
                    self.load_module(cls, comment=comment)

    # noinspection PyTypeChecker,PyTypeChecker
    def load_all_modules(self, submodules: Iterable[ModuleType]) -> None:
        """ Load available module """
        LOGGER.info("Loading plugins")
        self._load_all_from_metamod(submodules)
        self.loaded = []
        for module in self.modules:
            self.loaded.append(module)
        self.helpable.sort(key=lambda x: x.name)
        LOGGER.info("Plugins loaded %s", self.loaded)

    def unload_all_modules(self) -> None:
        """ Unload modules """
        LOGGER.info("Unloading modules...")

        # Can't modify while iterating, so collect a list first
        for mod in list(self.modules.values()):
            self.unload_module(mod)

        LOGGER.info("All modules unloaded.")

    async def migrate_chat(self, old_chat: int, new_chat: int):
        """ Run all migrate handler on every migrateable module """
        LOGGER.debug("Migrating chat from %s to %s", old_chat, new_chat)
        for mod in self.__migrateable:
            await mod.__migrate__(old_chat, new_chat)

    async def help_builder(self, module_list: list, prefix: str, chat_id) -> List:
        """ Build the help button """
        modules = [
            InlineKeyboardButton(
                # await self.text(chat_id, f"{x.name.lower()}_button"),
                x.name,
                callback_data="{}_module({})".format(prefix, x.name.lower()))
            for x in module_list
        ]

        pairs = [
            modules[i * 3:(i + 1) * 3]
            for i in range((len(modules) + 3 - 1) // 3)
        ]
        return pairs
