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
from typing import Any, Iterable, MutableMapping, Optional, Type

from .. import plugin

LOGGER = logging.getLogger(__name__)


class PluginExtender:
    modules: MutableMapping[str, plugin.Plugin]

    def __init__(self, **kwargs: Any) -> None:
        self.modules = {}

        super().__init__(**kwargs)

    def load_module(
            self, cls: Type[plugin.Plugin], *, comment: Optional[str] = None
        ) -> None:
        """ Load bot module"""
        LOGGER.info("Loading %s", cls.format_desc(comment))

        mod = cls(self)
        mod.comment = comment
        self.modules[cls.name] = mod

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
        LOGGER.info("All plugins loaded.")

    def unload_all_modules(self) -> None:
        """ Unload modules """
        LOGGER.info("Unloading modules...")

        # Can't modify while iterating, so collect a list first
        for mod in list(self.modules.values()):
            self.unload_module(mod)

        LOGGER.info("All modules unloaded.")
