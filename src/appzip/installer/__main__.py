import sys
from platform import python_version
import logging
import os
import time
import datetime as dt

from .metadata import Metadata
from .colorize import get_theme

START_TIME = time.perf_counter_ns()

log = logging.getLogger()

STREAM = sys.stdout
theme = get_theme(STREAM)

# noinspection PyArgumentList
logging.basicConfig(
    stream=STREAM,
    level=logging.DEBUG if os.environ.get("DEBUG") else logging.WARNING,
    formatter=logging.Formatter(
        fmt="{theme.log_time}[{asctime}.{msecs:0<3.0f}]{theme.reset} {theme:{levelname}} {theme:{message}}",
        datefmt="%H:%M:%S",
        style="{",
        defaults={"theme": theme},
    )
)


def main():
    # Opening message.
    theme.print("[dim]Installing...")

    # Load metadata.
    log.info("Loading metadata...")
    metadata = Metadata()
    log.debug(metadata)

    # Verify proper python version.
    log.debug("Checking python version...")
    if metadata.minimum_python > sys.hexversion:
        s = f"{metadata.minimum_python:0>8x}"
        theme.exit(f"[error]Installer requires Python >={int(s[:2], 16)}.{int(s[2:4], 16)}, not {python_version()}")

    # Exit message.
    runtime = dt.timedelta(microseconds=(time.perf_counter_ns() - START_TIME) / 1000)
    log.debug(f"Finished in [runtime]{runtime}")
    theme.print(f"[dim]Finished in [runtime]{runtime}")
    theme.print(f"Installed [name]{metadata.name}[/] [version]{metadata.version}[/]")
