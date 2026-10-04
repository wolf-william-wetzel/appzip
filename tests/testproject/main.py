import os
from pathlib import Path

def main():
    print("Project running...")

    from src import foobar
    print(f"Code found: {foobar.__file__}")

    os.access(Path(__file__).parent / "media" / "file.txt", os.R_OK)
    print("Media found.")

    import requests  # noqa
    print(f"Modules loaded: {requests.__file__}")

    print("Successful run.")
