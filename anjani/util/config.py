import os
from typing import Any

from dotenv import load_dotenv


class TelegramConfig:

    def __init__(self) -> None:
        load_from_file = False
        if os.path.isfile("config.env"):
            load_from_file = True
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
            if load_from_file and value == "":
                value = None

            if value is not None and key == "api_id":
                value = int(value)

            setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        return self.__getattribute__(name)

    def __getitem__(self, item: str) -> Any:
        return self.__getattr__(item)
