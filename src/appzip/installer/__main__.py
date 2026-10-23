import sys
from platform import python_version

from .metadata import Metadata
from .colorize import get_theme


def main():
    # Initialize installer.
    theme = get_theme(sys.stdout)
    metadata = Metadata()
    print(f"{theme.log_info}Running installer...{theme.reset}")

    # Verify proper python version.
    if metadata.minimum_python > sys.hexversion:
        s = f"{metadata.minimum_python:0>8x}"
        raise SystemExit(f"Installer requires Python >={int(s[:2], 16)}.{int(s[2:4], 16)}, not {python_version()}")

    # Exit message.
    print(f"{theme.log_warning}Done!{theme.reset}")
