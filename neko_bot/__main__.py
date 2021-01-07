"""Bot main starter"""

from neko_bot import neko
from neko_bot.core import setup_log


if __name__ == "__main__":
    setup_log()
    neko.begin()
