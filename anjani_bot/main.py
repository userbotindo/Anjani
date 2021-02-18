import asyncio
import logging

from . import anjani, setup_log


def main():
    log = logging.getLogger(__name__)
    setup_log()
    log.info("Loading code...")
    anjani.begin()


if __name__ == "__main__":
    main()
