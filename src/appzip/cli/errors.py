import warnings
import logging
from pathlib import Path

from msgspec import DecodeError, ValidationError

from .utils import format_path

log = logging.getLogger(__name__)

__all__ = (
    "AppzipError",
    "RmtreeError",
    "AppzipWarning",
    "SymlinkWarning",
    "DecodeError",
    "ValidationError",
)


class AppzipError(Exception):
    pass


class RmtreeError(AppzipError):
    def __init__(self, base: Path, failures: list[tuple[str, BaseException]]):
        super().__init__("\n".join(f"{format_path(Path(n), base)} -> {e}" for n, e in failures))


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
