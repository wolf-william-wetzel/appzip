from dataclasses import dataclass
import json


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


@dataclass
class Metadata:
    name: str
    version: str
    description: str
    minimum_python: int
    dependencies: list[str]
    entry_points: list[EntryPoint]

    @staticmethod
    def _json_object_hook(obj: dict):
        if obj.keys() == {"name", "value", "group"}:
            return EntryPoint(**obj)
        return obj

    @classmethod
    def from_json(cls, json_str: str | bytes | bytearray):
        return cls(**json.loads(json_str, object_hook=cls._json_object_hook))
