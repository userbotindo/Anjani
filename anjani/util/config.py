from os import cpu_count, getenv
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from anjani import DEFAULT_CONFIG_PATH


class Config:
    API_ID: str
    API_HASH: str
    BOT_TOKEN: str
    OWNER_ID: int
    WORKERS: int
    DOWNLOAD_PATH: Optional[str]

    DB_URI: str

    SW_API: Optional[str]
    LOG_CHANNEL: Optional[str]
    ALERT_LOG: Optional[str]

    LOGIN_URL: Optional[str]
    PLUGIN_FLAG: list[str]

    IS_CI: bool

    def __init__(self) -> None:
        config_path = Path(DEFAULT_CONFIG_PATH)
        if config_path.is_file():
            load_dotenv(config_path)

        self.API_ID = getenv("API_ID", "")
        self.API_HASH = getenv("API_HASH", "")
        self.BOT_TOKEN = getenv("BOT_TOKEN", "")
        self.OWNER_ID = int(getenv("OWNER_ID", 0))
        self.WORKERS = int(getenv("WORKERS", min(32, (cpu_count() or 0) + 4)))
        self.DOWNLOAD_PATH = getenv("DOWNLOAD_PATH", "./downloads")

        self.DB_URI = getenv("DB_URI", "")

        self.LOG_CHANNEL = getenv("LOG_CHANNEL")
        self.ALERT_LOG = getenv("ALERT_LOG")
        self.SW_API = getenv("SW_API")

        self.LOGIN_URL = getenv("LOGIN_URL")
        self.PLUGIN_FLAG = [i.strip() for i in getenv("PLUGIN_FLAG", "").split(";")]

        self.IS_CI = getenv("IS_CI", "false").lower() == "true"

        #  check if all the required variables are set
        if any(
            {
                not self.API_ID,
                not self.API_HASH,
                not self.BOT_TOKEN,
                not self.DB_URI,
            }
        ):
            raise RuntimeError("Required ENV variables are missing!")

        # create download path if not exists
        Path(self.DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)

    def is_plugin_disabled(self, plugin_name: str) -> bool:
        return plugin_name in self.PLUGIN_FLAG
