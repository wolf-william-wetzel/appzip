import json
from zipfile import ZipFile
from pathlib import Path
from dataclasses import dataclass
from pprint import pformat

PYZ_PATH = Path(__file__).parent.parent


@dataclass
class EntryPoint:
    name: str
    value: str
    group: str
    module: str = ""
    attr: str = ""
    console: bool = False
    app: bool = False
    windowed: bool = False

    def __post_init__(self):
        self.module, _, self.attr = self.value.partition(":")
        self.console = self.group.startswith("appzip.ep.console")
        self.app = self.group.startswith("appzip.ep.app")
        self.windowed = self.group.endswith(".w")


def json_object_hook(obj: dict):
    if obj.keys() == {"name", "value", "group"}:
        return EntryPoint(**obj)
    return obj


class Metadata:
    name: str
    version: str
    description: str
    minimum_python: int
    dependencies: list[str]
    entry_points: list[EntryPoint]

    def __init__(self):
        with ZipFile(PYZ_PATH) as zf:
            self.data = json.loads(zf.read("metadata.json").decode("utf-8"), object_hook=json_object_hook)

    def __getattr__(self, name: str):
        if name not in self.data:
            raise AttributeError(f"Unknown metadata attribute: '{name}'")
        return self.data[name]

    def __repr__(self):
        return pformat(
            self.data,
            indent=2,
            expand=True,
            sort_dicts=False,
        ).replace("\n", "\n" + " " * 24).replace("EntryPoint", "[magenta]EntryPoint[/]")
