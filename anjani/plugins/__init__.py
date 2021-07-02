import importlib
import pkgutil
from pathlib import Path

current_dir = str(Path(__file__).parent)
subplugins = [
    importlib.import_module("." + info.name, __name__)
    for info in pkgutil.iter_modules([current_dir])
]

try:
    _reload_flag: bool

    # noinspection PyUnboundLocalVariable
    if _reload_flag:
        # Plugin has been reloaded, reload our subplugins
        for plugin in subplugins:
            importlib.reload(plugin)
except NameError:
    _reload_flag = True