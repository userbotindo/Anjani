import logging

from . import launch, log

logs = logging.getLogger("launch")
log.setup_log()

logs.info("Loading code")


def main():
    """Main entry point for the default bot command."""

    launch.main()


if __name__ == "__main__":
    main()