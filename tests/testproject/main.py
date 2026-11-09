import os
from pathlib import Path
import sys


def _main():
    # General info.
    print(f"Python: {sys.executable}")
    parent = Path(__file__).parent
    print(f"Parent dir: {parent}")

    # Source code access.
    print("\nTesting code access...")
    from src import foobar  # noqa
    print(f"Code found: {foobar.__file__}")

    # Media access.
    print("\nAccessing media...")
    path = parent / "media" / "file.txt"
    assert os.access(path, os.R_OK), "Can't access media."
    print(f"Media found: {path}")

    # Symlink media access.
    print("\nAccessing symlink media...")
    path = parent / "media_link" / "file.txt"
    assert os.access(path.resolve(), os.R_OK), "Can't access symlink media."
    print(f"Symlink media found: {path}")

    # Symlink file access.
    print("\nAccessing symlink file...")
    path = parent / "file.txt"
    assert os.access(path, os.R_OK), "Can't access symlink file."
    print(f"Symlink found: {path} -> {path.readlink()}")

    # Excluded nodes are missing.
    print("\nSearching for excluded files...")
    excluded_nodes = ["ext_link", "exclude.txt", "hidden"]
    for p in excluded_nodes:
        path = parent / p
        if path.exists():
            print(f"ERROR: excluded node exists: {p}")

    # Dependencies available.
    print("\nImporting dependencies...")
    import requests  # noqa
    print(f"Module loaded: {requests.__file__}")
    import tomli_w  # noqa
    print(f"Module loaded: {tomli_w.__file__}")

    print("\nSuccessful run.")


def main():
    try:
        _main()
    except BaseException as exc:
        print(exc)
    finally:
        input("Press ENTER to quit...")


if __name__ == "__main__":
    main()
