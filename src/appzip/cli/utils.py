from pathlib import Path
from functools import cache

HOME = Path.home()
CWD = Path.cwd()  # Shouldn't change throughout program run.

path_abbrev = {
    CWD: ".",
    HOME: "~",
    CWD.parent: "..",
}
DEFAULT_ABBREV = "..."


@cache
def format_path(path: Path, parents: tuple[Path, ...] = (CWD, HOME)) -> str:
    dir_str = "/" if path.is_dir() else ""
    for parent in parents:
        if path.is_relative_to(parent):
            return f"{path_abbrev.get(parent, DEFAULT_ABBREV)}/{path.relative_to(parent).as_posix()}{dir_str}"
    if path.is_absolute():
        return f"{path.as_posix()}{dir_str}"
    return f"{DEFAULT_ABBREV}/{path.as_posix()}{dir_str}"
