from dataclasses import is_dataclass, fields
from functools import singledispatch
import datetime as dt
from types import EllipsisType
from pathlib import Path

INDENT = 2


@singledispatch
def prepr(obj, indent: int = 0) -> str:
    if is_dataclass(obj) and not isinstance(obj, type):
        spaces, level = " " * indent, " " * INDENT
        header = f"[name]{obj.__class__.__name__}[/][brace]([/]"
        middle = []
        for f in fields(obj):
            middle.append(
                f"{spaces}{level}[attr]{f.name}[/]={prepr(getattr(obj, f.name), indent=indent + INDENT)},"
            )
        footer = f"{spaces}[brace])[/]"
        return "\n".join((header, *middle, footer))
    return str(obj)

@prepr.register
def _(obj: list | tuple, indent: int = 0) -> str:
    spaces, level = " " * indent, " " * INDENT
    braces = "[]" if isinstance(obj, list) else "()"
    header = f"[brace]{braces[0]}[/]"
    middle = []
    for item in obj:
        middle.append(
            f"{spaces}{level}{prepr(item, indent=indent + INDENT)},"
        )
    footer = f"{spaces}[brace]{braces[1]}[/]"
    return "\n".join((header, *middle, footer))

@prepr.register
def _(obj: dict, indent: int = 0) -> str:
    spaces, level = " " * indent, " " * INDENT
    header = f"[brace]{{[/]"
    middle = []
    for key, item in obj.items():
        middle.append(
            f"{spaces}{level}{prepr(key, indent=indent + INDENT)}: {prepr(item, indent=indent + INDENT * 2)},"
        )
    footer = f"{spaces}[brace]}}[/]"
    return "\n".join((header, *middle, footer))

@prepr.register
def _(obj: str, indent: int = 0) -> str:
    return f"[string]{obj!r}[/]"

@prepr.register
def _(obj: EllipsisType, indent: int = 0) -> str:
    return "[ellipsis]...[/]"

@prepr.register
def _(obj: Path, indent: int = 0) -> str:
    if obj.is_dir():
        return f"[path]{obj.as_posix()}/[/]"
    return f"[path]{obj.parent.as_posix()}/[/][filename]{obj.name}[/]"

@prepr.register
def _(obj: dt.timedelta, indent: int = 0) -> str:
    return f"[time]{obj}[/]"

@prepr.register
def _(obj: None, indent: int = 0) -> str:
    return "[none]None[/]"

@prepr.register
def _(obj: bool, indent: int = 0) -> str:
    return f"[{'true' if obj else 'false'}]{obj!r}[/]"

@prepr.register
def _(obj: int | float | complex, indent: int = 0) -> str:
    return f"[number]{obj!r}[/]"

@prepr.register
def _(obj: bytes, indent: int = 0) -> str:
    return f"[bytes]{obj!r}[/]"

@prepr.register
def _(obj: bytearray, indent: int = 0) -> str:
    return f"[name]bytearray[/][brace]([/]{prepr(bytes(obj))}[brace])[/]"
