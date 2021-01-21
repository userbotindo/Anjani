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
        LOGGER.info(f"Loading {cls.format_desc(comment)}")

        mod = cls(self)
        mod.comment = comment
        self.modules[cls.name] = mod

    def unload_module(self, mod: plugin.Plugin) -> None:
        cls = type(mod)
        LOGGER.info(f"Unloading {mod.format_desc(mod.comment)}")

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
    def load_all_modules(self) -> None:
        LOGGER.info("Loading plugins")
        self._load_all_from_metamod(self.submodules)
        LOGGER.info("All plugins loaded.")

    def unload_all_modules(self) -> None:
        LOGGER.info("Unloading modules...")

        # Can't modify while iterating, so collect a list first
        for mod in list(self.modules.values()):
            self.unload_module(mod)

        LOGGER.info("All modules unloaded.")
