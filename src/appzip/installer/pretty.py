import time
from dataclasses import is_dataclass, fields, MISSING
from functools import singledispatch
import datetime as dt
from types import EllipsisType, NotImplementedType, SimpleNamespace
from argparse import Namespace
from pathlib import Path
import os
import zipfile
from collections import Counter
import stat

INDENT = 2
TIMESTAMP_TEMPLATE = "[timestamp]{0}-{1}-{2} {3:0>2}:{4:0>2}:{5:0>2}[/]"


class Char:
    INDENT = "[indent]\u2502[/]"
    TREE_TRUNK = "[tree]\u2502[/]"
    TREE_BRANCH = "[tree]\u251c[/]"
    TREE_LAST = "[tree]\u2514[/]"
    TREE_LEAF = "[tree]\u2500[/]"


def _make_indent(indent: int) -> str:
    return f"{Char.INDENT}{' ' * (INDENT - 1)}" * (indent // INDENT)


def _make_lines(header: str, middle: list[str], footer: str | None = None, **kwargs) -> str:
    indent: int = kwargs.get("indent", 0)
    lines = [_make_indent(indent + INDENT) + line for line in middle]
    if not lines:
        return header + ("" if footer is None else footer)
    if footer is not None:
        lines.append(_make_indent(indent) + footer)
    return "\n".join((header, *lines))


def _prepr_dataclass(obj, **kwargs) -> str:
    indent = kwargs.get("indent", 0)
    middle = []
    for f in fields(obj):
        if not f.init:
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


def _format_bytes(number: int) -> str:
    for limit, unit in zip((1<<p for p in range(40, 0, -10)), "TGMK"):
        if abs(number) >= limit:
            return f"{number / limit:,.2f} {unit}B"
    return f"{number} B"


def _style_zipinfo_name(name: str, symlink: bool = False) -> str:
    stem = name.removesuffix("/").rpartition("/")[2]
    style = "[file]"
    if symlink:
        style = "[symlink]"
    elif name.endswith("/"):
        style = "[dir]"
    elif name.endswith(".py") or name.endswith(".pyw"):
        style = "[pyfile]"
    if stem.startswith("__"):
        style += "[dunder_file]"
    if stem.startswith("."):
        style += "[dotfile]"
    return f"{style}{stem}[/]"


def _make_zipinfo_name(obj: zipfile.ZipInfo, **kwargs) -> str:
    size_str = f"{_format_bytes(kwargs.get("sizes", {}).get(obj.filename) or obj.file_size)}"
    time_str = TIMESTAMP_TEMPLATE.format(*obj.date_time)
    mode = obj.external_attr >> 16
    is_link = stat.S_ISLNK(mode)
    name = _style_zipinfo_name(obj.filename, is_link)
    if is_link:
        if zf := kwargs.get("zf", ""):
            target = zf.read(obj).decode("utf-8")
        else:
            target = kwargs.get("symlink_target", "")
        if target:
            parents = target.removesuffix("/").rpartition("/")[0]
            parents = f"[dir]{parents}/" if parents else ""
            name += f" [d][l_yellow]-> {parents}[/]{_style_zipinfo_name(target)}"
    return f"{name} [filesize]{size_str}[/] [filemode]{stat.filemode(mode)}[/] {time_str}"


def _prepr_zipdir(header: str, parent: Path = Path(), **kwargs) -> str:
    indent: str = kwargs.get("indent", "")
    middle = []
    infolist = kwargs["zf"].infolist() if "zf" in kwargs else []
    children = [i for i in infolist if Path(i.filename).parent == parent]
    for i, info in enumerate(children):
        last = i == len(children) - 1
        pre_string = indent + (Char.TREE_BRANCH, Char.TREE_LAST)[last] + Char.TREE_LEAF
        kws = kwargs | {"indent": indent + (Char.TREE_TRUNK + " ", "  ")[last]}
        middle.append(f"{pre_string}{prepr(info, **kws)}")
    return "\n".join((header, *middle))


def _calculate_zipfile_sizes(zf: zipfile.ZipFile) -> Counter[str]:
    sizes = Counter()
    for info in zf.infolist():
        sizes[info.filename] += info.file_size
        sizes += {p.as_posix() + "/": info.file_size for p in Path(info.filename).parents}
    return sizes


@singledispatch
def prepr(obj, **kwargs) -> str:
    # Dataclass instance.
    if is_dataclass(obj):
        return _prepr_dataclass(obj, **kwargs)
    # Default to str.
    return str(obj)

@prepr.register
def _(obj: zipfile.ZipFile, **_) -> str:
    sizes = _calculate_zipfile_sizes(obj)
    name = "[error]Unnamed Archive"
    size = sizes["./"]
    mode = ""
    timestamp = ""
    if obj.filename:
        name = obj.filename.rpartition(os.path.sep)[2]
        st = Path(obj.filename).stat()
        size = st.st_size
        mode = stat.filemode(st.st_mode)
        timestamp = TIMESTAMP_TEMPLATE.format(*time.localtime(st.st_mtime)[:6])
    return _prepr_zipdir(
        f"[name]{name} [filesize]{_format_bytes(size)}[/] [filemode]{mode}[/] {timestamp}",
        sizes=sizes,
        zf=obj,
        recurse=True,
    )

@prepr.register
def _(obj: zipfile.ZipInfo, **kwargs) -> str:
    name = _make_zipinfo_name(obj, **kwargs)
    if obj.is_dir() and kwargs.get("recurse", False):
        return _prepr_zipdir(name, Path(obj.filename), **kwargs)
    return name

@prepr.register
def _(obj: list, indent: int = 0) -> str:
    return _make_lines(
        "[brace][[/]",
        [f"{prepr(item, indent=indent + INDENT)}," for item in obj],
        "[brace]][/]",
        indent=indent,
    )

@prepr.register
def _(obj: SimpleNamespace | Namespace, indent: int = 0) -> str:
    return _make_lines(
        f"[name]{type(obj).__name__}[/][brace]([/]",
        [f"[attr]{name}[/]={prepr(value, indent=indent + INDENT)}" for name, value in vars(obj).items()],
        "[brace])[/]",
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
def _(obj: type, **_) -> str:
    return f"[name]{obj.__name__}[/]"

@prepr.register
def _(_obj: EllipsisType, **_) -> str:
    return "[ellipsis]...[/]"

@prepr.register
def _(obj: NotImplementedType, **_) -> str:
    return f"[notimpl]{obj}[/]"

@prepr.register
def _(obj: Path, **kwargs) -> str:
    if obj.is_dir() or kwargs.get("force_dir"):
        return f"[path]{obj}{os.path.sep}[/]"
    return f"[path]{obj.parent}{os.path.sep}[/][filename]{obj.name}[/]"

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
