import os
from typing import Any, ClassVar, Iterator, MutableMapping, TypeVar

_KT = TypeVar("_KT", bound=str, contravariant=True)
_VT = TypeVar("_VT", covariant=True)


class TelegramConfig(MutableMapping[_KT, _VT]):

    __data: ClassVar[MutableMapping[_KT, _VT]] = {}

    def __init__(self) -> None:

        config: MutableMapping[Any, Any] = {
            "api_id": os.environ.get("API_ID"),
            "api_hash": os.environ.get("API_HASH"),
            "bot_token": os.environ.get("BOT_TOKEN"),
            "db_uri": os.environ.get("DB_URI"),
            "download_path": os.environ.get("DOWNLOAD_PATH"),
            "owner_id": os.environ.get("OWNER_ID"),
            "sp_token": os.environ.get("SP_TOKEN"),
            "sp_url": os.environ.get("SP_URL"),
            "sw_api": os.environ.get("SW_API"),
            "log_channel": os.environ.get("LOG_CHANNEL"),
        }

        for key, value in config.items():
            if not value:
                continue

            super().__setattr__(key, value)
            self.__data[key] = value

    def __delattr__(self, obj: object) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Can't delete configuration while running the bot.")

    def __delitem__(self, k: _KT) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Can't delete configuration while running the bot.")

    def __getattr__(self, name: str) -> _VT:
        return self.__getattribute__(name)

    def __getitem__(self, k: _KT) -> _VT:
        return self.__data[k]

    def __iter__(self) -> Iterator[_KT]:
        return self.__data.__iter__()

    def __len__(self) -> int:
        return len(self.__data)

    def __setattr__(self, name: str, value: Any) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Configuration must be done before running the bot.")

    def __setitem__(self, k: str, v: Any) -> None:  # skipcq: PYL-W0613
        raise RuntimeError("Configuration must be done before running the bot.")
