from dataclasses import dataclass
import json
from sys import hexversion

from .utils import get_python


EP_TEMPLATE = """#!{interpreter}
import subprocess
subprocess.run([{interpreter!r}, {script}], cwd={cwd!r})"""
EP_ATTR_TEMPLATE = "'-c', 'import {mod};{mod}.{fn}()'"


@dataclass
class EntryPoint:
    name: str
    value: str
    group: str
    module: str
    attr: str = ""
    console: bool = False
    app: bool = False
    windowed: bool = False

    def __post_init__(self):
        self.console = self.group.startswith("appzip.ep.console")
        self.app = self.group.startswith("appzip.ep.app")
        self.windowed = self.group.endswith(".w")

    def get_file_text(self, venv_dir, cwd) -> str:
        script = EP_ATTR_TEMPLATE.format(mod=self.module, fn=self.attr) if self.attr else repr(self.module)
        return EP_TEMPLATE.format(interpreter=get_python(venv_dir, self.windowed), script=script, cwd=str(cwd))


@dataclass
class Metadata:
    name: str
    version: str
    description: str
    minimum_python: int
    dependencies: list[str]
    entry_points: list[EntryPoint]
    base_name: str
    folder_name: str = ""
    app_name: str = ""
    python_valid: bool = True
    min_python_str: str = ""

    def __post_init__(self):
        self.folder_name = f"{self.name}_{self.version}" if self.version else self.name
        app_name = f"[app]{self.name}[/]"
        self.app_name = f"{app_name} [version]{self.version}[/]" if self.version else app_name
        self.python_valid = self.minimum_python <= hexversion
        py_hex_str = f"{self.minimum_python:0>8x}"
        self.min_python_str = f"{int(py_hex_str[:2], 16)}.{int(py_hex_str[2:4], 16)}"

    @staticmethod
    def _json_object_hook(obj: dict):
        if {"name", "value", "group"} <= obj.keys():
            return EntryPoint(**obj)
        return obj

    @classmethod
    def from_json(cls, json_str: str | bytes | bytearray):
        return cls(**json.loads(json_str, object_hook=cls._json_object_hook))
