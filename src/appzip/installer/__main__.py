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

console = Console(sys.stdout)

log = logging.getLogger()
logging.basicConfig(
    level=logging.DEBUG if os.environ.get("DEBUG") else logging.WARNING,
    handlers=[console.get_logging_handler()],
)


def fatal(message: str, code: int = 1):
    """Exit due to fatal error."""
    log.critical(message)
    console.exit(message, code)


def main():
    # Opening message.
    console.print("[dim]Running installer...")

    # Load metadata.
    log.info("Loading metadata...")
    with ZipFile(PYZ_PATH) as zf:
        metadata = Metadata.from_json(zf.read("metadata.json"))
    log.debug(metadata)

    # Verify proper python version.
    log.debug("Checking python version...")
    if metadata.minimum_python > sys.hexversion:
        s = f"{metadata.minimum_python:0>8x}"
        fatal(f"[error]Installer requires Python >={int(s[:2], 16)}.{int(s[2:4], 16)}, not {python_version()}")

    # Exit message.
    runtime = dt.timedelta(microseconds=(time.perf_counter_ns() - START_TIME) / 1000)
    log.debug(f"Finished in [runtime]{runtime}")
    console.print(f"[dim]Finished in [runtime]{runtime}")
    console.print(f"Installed [name]{metadata.name}[/] [version]{metadata.version}[/]")
