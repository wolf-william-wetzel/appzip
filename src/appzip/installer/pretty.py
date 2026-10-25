from dataclasses import is_dataclass, fields, MISSING
from functools import singledispatch
import datetime as dt
from types import EllipsisType, NotImplementedType, SimpleNamespace
from pathlib import Path
import inspect

INDENT = 2


def _make_indent(indent: int) -> str:
    return f"[indent]\u2502[/]{' ' * (INDENT - 1)}" * (indent // INDENT)


def _make_lines(header: str, middle: list[str], footer: str | None = None, **kwargs) -> str:
    indent: int = kwargs.get("indent", 0)
    lines = [_make_indent(indent + INDENT) + line for line in middle]
    if not lines:
        return header + ("" if footer is None else footer)
    if footer is not None:
        lines.append(_make_indent(indent) + footer)
    return "\n".join((header, *lines))


def _format_doc(doc: str) -> list[str]:
    doc_split = 80
    lines: list[str] = []
    for line in doc.splitlines():
        if len(line) < doc_split:
            lines.append(line)
            continue
        lines.append(line[:doc_split])
        lines.append(line[doc_split:])
    return [f"[doc]{line}[/]" for line in ['"""', *lines, '"""']]


@singledispatch
def prepr(obj, indent: int = 0) -> str:
    # Dataclass instance.
    if is_dataclass(obj):
        middle = []
        for f in fields(obj):
            if not f.repr:
                continue
            if (value := getattr(obj, f.name)) == f.default:
                continue
            if f.default_factory is not MISSING and value == f.default_factory():
                continue
            middle.append(f"[attr]{f.name}[/]={prepr(value, indent=indent + INDENT)},")
        return _make_lines(
            f"[name]{type(obj).__name__}[/][brace]([/]",
            middle,
            "[brace])[/]",
            indent=indent,
        )
    # Default to str.
    return str(obj)

@prepr.register
def _(obj: SimpleNamespace, indent: int = 0) -> str:
    return _make_lines(
        f"[name]{type(obj).__name__}[/][brace]([/]",
        [f"[attr]{name}[/]={prepr(value, indent=indent + INDENT)}" for name, value in vars(obj).items()],
        "[brace])[/]",
        indent=indent,
    )

@prepr.register
def _(obj: list, indent: int = 0) -> str:
    return _make_lines(
        "[brace][[/]",
        [f"{prepr(item, indent=indent + INDENT)}," for item in obj],
        "[brace]][/]",
        indent=indent,
    )

@prepr.register
def _(obj: tuple, indent: int = 0) -> str:
    return _make_lines(
        "[brace]([/]",
        [f"{prepr(item, indent=indent + INDENT)}," for item in obj],
        "[brace])[/]",
        indent=indent,
    )

@prepr.register
def _(obj: set, indent: int = 0) -> str:
    if not obj:
        return f"[name]{type(obj).__name__}[/][brace]()[/]"
    return _make_lines(
        "[brace]{[/]",
        [f"{prepr(item, indent=indent + INDENT)}," for item in obj],
        "[brace]}[/]",
        indent=indent,
    )

@prepr.register
def _(obj: frozenset, indent: int = 0) -> str:
    return _make_lines(
        f"[name]{type(obj).__name__}[/][brace]({{[/]",
        [f"{prepr(item, indent=indent + INDENT)}," for item in obj],
        "[brace]})[/]",
        indent=indent,
    )

@prepr.register
def _(obj: dict, indent: int = 0) -> str:
    return _make_lines(
        "[brace]{[/]",
        [f"{prepr(key, indent=indent + INDENT)}: {prepr(item, indent=indent + INDENT)},"
         for key, item in obj.items()],
        "[brace]}[/]",
        indent=indent,
    )

@prepr.register
def _(obj: str, **_) -> str:
    return f"[string]{obj!r}[/]"

@prepr.register
def _(obj: type, **kwargs) -> str:
    indent = kwargs.get("indent", 0)
    # Dataclass class.
    if is_dataclass(obj):
        header = f"[dataclass]@dataclass[/] [name]{obj.__name__}[/]:"
        middle = []
        if doc := inspect.getdoc(obj):
            middle.extend(_format_doc(doc))
        kw = False
        for f in fields(obj):  # noqa
            if not f.repr:
                continue
            if not kw and f.kw_only:
                kw = True
                middle.append("[brace]*[/]")
            middle.append(f"[attr]{f.name}[/]: [hint]{f.type.__name__}[/]")
            if f.default is not MISSING:
                middle[-1] += f" = [default]{prepr(f.default, indent=indent + INDENT)}[/]"
            if f.default_factory is not MISSING:
                middle[-1] += f" = [default]{prepr(f.default_factory, indent=indent + INDENT)}[/]"
        return _make_lines(header, middle, None, indent=indent)
    return f"[name]{obj.__name__}[/]"

@prepr.register
def _(_obj: EllipsisType, **_) -> str:
    return "[ellipsis]...[/]"

@prepr.register
def _(obj: NotImplementedType, **_) -> str:
    return f"[notimpl]{obj}[/]"

@prepr.register
def _(obj: Path, **_) -> str:
    if obj.is_dir():
        return f"[path]{obj.as_posix()}/[/]"
    return f"[path]{obj.parent.as_posix()}/[/][filename]{obj.name}[/]"

@prepr.register
def _(obj: dt.timedelta | dt.date | dt.time | dt.datetime, **_) -> str:
    return f"[time]{obj}[/]"

@prepr.register
def _(obj: None, **_) -> str:
    return f"[none]{obj}[/]"

@prepr.register
def _(obj: bool, **_) -> str:
    return f"[{'true' if obj else 'false'}]{obj}[/]"

@prepr.register
def _(obj: int | float | complex, **_) -> str:
    return f"[number]{obj}[/]"

@prepr.register
def _(obj: bytes, **_) -> str:
    return f"[bytes]{obj}[/]"

@prepr.register
def _(obj: bytearray, **_) -> str:
    return f"[name]{type(obj).__name__}[/][brace]([/]{prepr(bytes(obj))}[brace])[/]"
