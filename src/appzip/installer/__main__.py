from .metadata import Metadata
from sys import hexversion
from platform import python_version


def main():
    print("Running installer...")
    metadata = Metadata()

    # Verify proper python version.
    if metadata.minimum_python > hexversion:
        s = f"{metadata.minimum_python:0>8x}"
        raise SystemExit(f"Installer requires Python >={int(s[:2], 16)}.{int(s[2:4], 16)}, not {python_version()}")

    # Exit message.
    print("Done!")
