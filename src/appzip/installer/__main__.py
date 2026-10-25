import sys
from platform import python_version
import logging
import os
import time
import datetime as dt
from pathlib import Path
from zipfile import ZipFile

from .metadata import Metadata
from .console import Console

START_TIME = time.perf_counter_ns()
PYZ_PATH = Path(__file__).parent.parent
STATUS = "[blink][l_green]\u25cf[/] "

console = Console(sys.stdout)

log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("DEBUG") else logging.WARNING,
    handlers=[console.get_logging_handler()],
)


def fatal(message: str, code: int = 1):
    """Exit due to fatal error."""
    log.critical(message)
    console.exit(f"[error]{message}", code)


def main():
    log.debug("Interactive: %s", console.interactive)

    # Load metadata.
    log.info("Loading metadata...")
    with console.status(f"{STATUS}Loading metadata..."):
        with ZipFile(PYZ_PATH) as zf:
            metadata = Metadata.from_json(zf.read("metadata.json"))
    log.debug(metadata)

    # Verify proper python version.
    log.info("Checking python version...")
    with console.status(f"{STATUS}Checking python version..."):
        py_hex_str = f"{metadata.minimum_python:0>8x}"
        major, minor = int(py_hex_str[:2], 16), int(py_hex_str[2:4], 16)
        if metadata.minimum_python > sys.hexversion:
            fatal(f"Installer requires Python >={major}.{minor}, not {python_version()}")
    log.debug(f"Python [string]{python_version()}[/] >= [string]{major}.{minor}[/]")

    # Exit message.
    runtime = dt.timedelta(microseconds=(time.perf_counter_ns() - START_TIME) / 1000)
    log.debug(f"Finished in [time]{runtime}")
    console.print(f"[dim]Finished in [time]{runtime}")
    console.print(f"Installed [l_green]{metadata.name}[/] [number]{metadata.version}[/]")
