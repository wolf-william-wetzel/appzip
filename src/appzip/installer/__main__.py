from .metadata import Metadata
import sys
import platform


def main():
    print("Running installer...")
    metadata = Metadata()

    # Verify proper python version.
    if metadata.minimum_python > sys.hexversion:
        minor = int(f"{metadata.minimum_python:0>8x}"[2:4], base=16)
        raise SystemExit(f"Installer requires Python 3.{minor}.0+, not {platform.python_version()}")

    # Exit message.
    print("Done!")
