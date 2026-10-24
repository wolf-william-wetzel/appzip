import sys
from platform import python_version
import logging
import os

from .metadata import Metadata
from .colorize import get_theme

log = logging.getLogger()

STREAM = sys.stdout
theme = get_theme(STREAM)
RESET = theme.reset

# noinspection PyArgumentList
logging.basicConfig(
    stream=STREAM,
    level=logging.DEBUG if os.environ.get("DEBUG") else logging.WARNING,
    formatter=logging.Formatter(
        fmt="{theme.log_time}[{asctime}.{msecs:0<3.0f}]{theme.reset} {theme:{levelname}} {message}",
        datefmt="%H:%M:%S",
        style="{",
        defaults={"theme": theme},
    )
)


def main():
    # Load metadata.
    log.info("Loading metadata...")
    metadata = Metadata()
    log.debug(metadata)

    # Verify proper python version.
    if metadata.minimum_python > sys.hexversion:
        s = f"{metadata.minimum_python:0>8x}"
        raise SystemExit(
            f"Installer requires Python >={int(s[:2], 16)}.{int(s[2:4], 16)}, not {python_version()}")

    # Exit message.
    print(f"Installed {theme.name}{metadata.name}{RESET} {theme.version}{metadata.version}{RESET}")
