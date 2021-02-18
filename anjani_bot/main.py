"""Entry point"""
import logging

from . import anjani, setup_log


def main():
    """Main entry point for the default bot command."""

    log = logging.getLogger(__name__)
    setup_log()
    log.info("Loading code...")
    anjani.begin()


if __name__ == "__main__":
    main()
