import os
from typing import Any, ClassVar, Iterator, MutableMapping, TypeVar

from dotenv import load_dotenv

_KT = TypeVar("_KT", str, str)
_VT = TypeVar("_VT", str, str)


class TelegramConfig(MutableMapping[_KT, _VT]):
    _length: ClassVar[int] = 0

    def __init__(self) -> None:
        if os.path.isfile("config.env"):
            load_dotenv("config.env")

        config = {
            "api_id": os.environ.get("API_ID"),
            "api_hash": os.environ.get("API_HASH"),
            "bot_token": os.environ.get("BOT_TOKEN"),
            "db_uri": os.environ.get("DB_URI"),
            "download_path": os.environ.get("DOWNLOAD_PATH"),
            "owner_id": os.environ.get("OWNER_ID"),
            "sw_api": os.environ.get("SW_API"),
            "log_channel": os.environ.get("LOG_CHANNEL")
        }

        for key, value in config.items():
            if not value:
                continue

            super().__setattr__(key, value)
            TelegramConfig._length += 1

    def __getattr__(self, name: _KT) -> _VT:
        return self.__getattribute__(name)

    def __getitem__(self, k: _KT) -> _VT:
        return self.__getattr__(k)

    def __setitem__(self, k: _KT, v: _VT) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Configuration must be done before running the bot.")

    def __setattr__(self, name: str, value: Any) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Configuration must be done before running the bot.")

    def __delitem__(self, v: _KT) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Can't delete configuration while running the bot.")

    def __iter__(self) -> Iterator[_KT]:
        return super().__iter__()

    def __len__(self) -> int:
        return self._length
