"""Module For NekoBot Configuration"""

from os import environ
from dotenv import load_dotenv


load_dotenv("config.env")


class Config:  # pylint: disable=too-few-public-methods
    """
    all available bot config from environ
    """

    # pyrogram required
    BOT_TOKEN = environ.get("BOT_TOKEN")
    API_ID = int(environ.get("API_ID"))
    API_HASH = environ.get("API_HASH")
    # Required
    DB_URI = environ.get("DB_URI")
    # Staff  required
    OWNER_ID = int(environ.get("OWNER_ID"))
