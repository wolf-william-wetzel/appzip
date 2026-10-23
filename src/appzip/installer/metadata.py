import json
from zipfile import ZipFile
from pathlib import Path

PYZ_PATH = Path(__file__).parent.parent


class Metadata:
    name: str
    version: str
    description: str
    minimum_python: int
    dependencies: list[str]
    entry_points: list[dict[str, str]]

    def __init__(self):
        with ZipFile(PYZ_PATH) as zf:
            self.data = json.loads(zf.read("metadata.json").decode("utf-8"))

    def __getattr__(self, name: str):
        if name not in self.data:
            raise AttributeError(f"Unknown metadata key: '{name}'")
        return self.data[name]
