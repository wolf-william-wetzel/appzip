from pathlib import Path
from functools import cache
import sys
import warnings
import logging

log = logging.getLogger(__name__)

IS_WIN = sys.platform == "win32"


class AppzipWarning(Warning):
    level: int = logging.WARNING

    @classmethod
    def warn(cls, message: str):
        warnings.warn(message, cls)


class SymlinkWarning(AppzipWarning):
    level = logging.ERROR


orig_show_warning = warnings.showwarning
def show_warning(message, category, filename, lineno, file=None, line=None):
    if issubclass(category, AppzipWarning):
        log.log(category.level, message)
        return
    orig_show_warning(message, category, filename, lineno, file, line)
warnings.showwarning = show_warning


HOME = Path.home()
CWD = Path.cwd()  # Shouldn't change throughout program run.

path_abbrev = {
    CWD: ".",
    CWD.parent: "..",
    HOME: "~",
}
DEFAULT_ABBREV = "..."


@cache
def format_path(path: Path, *args: Path, force_dir: bool = False) -> str:
    """Format ``path`` as posix, shortening it if possible.

    If ``path`` is a directory, append a trailing slash.
    Check for shortening in the following order: ``.``, ``..``, ``~``.
    Extra args will be searched before the defaults, with a replacement string of ``...``.
    """
    dir_str = "/" if force_dir or path.is_dir() else ""
    for parent in args + tuple(path_abbrev.keys()):
        if path.is_relative_to(parent):
            return f"{path_abbrev.get(parent, DEFAULT_ABBREV)}/{path.relative_to(parent).as_posix()}{dir_str}"
    return f"{'' if path.is_absolute() else f'{DEFAULT_ABBREV}/'}{path.as_posix()}{dir_str}"


def format_node(node: Path, base: Path, real: Path | None = None) -> str:
    """Format ``node`` with an optional real path for symlinks. Both will be checked against ``base``."""
    return f"{format_path(node, base)}{f' -> {format_path(real, base)}' if real else ''}"
