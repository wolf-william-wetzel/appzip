import os
import sys
import logging


def getenv(var: str, fallback: str = "") -> str:
    try:
        return os.environ.get(var, fallback)
    except Exception:  # noqa
        return fallback


level_str = "WARNING"  # Default level.
if level := getenv("LOGLEVEL"):
    level_str = level
elif level := getenv("LOG_LEVEL"):
    level_str = level
elif getenv("DEBUG"):
    level_str = "DEBUG"
LOG_LEVEL: int = logging.getLevelNamesMapping().get(level_str.upper(), logging.WARNING)
del level_str


def is_term(file=None) -> bool:
    """Modified from the Python 3.15 stdlib."""
    if file is None:
        file = sys.stdout

    if getenv("TTY_COMPATIBLE") == "1":
        return True
    if getenv("TTY_COMPATIBLE") == "0":
        return False

    if getenv("TERM") in ("dumb", "unknown"):
        return False

    if not hasattr(file, "fileno"):
        return False

    try:
        return os.isatty(file.fileno())
    except OSError:
        try:
            return hasattr(file, "isatty") and file.isatty()
        except ValueError:
            return False


def can_interact(file=None) -> bool:
    if getenv("TTY_INTERACTIVE") == "1":
        return True
    if getenv("TTY_INTERACTIVE") == "0":
        return False
    return is_term(file)


def can_colorize(file=None) -> bool:
    """Modified from the Python 3.15 stdlib."""
    if not sys.flags.ignore_environment:
        if getenv("PYTHON_COLORS") == "0":
            return False
        if getenv("PYTHON_COLORS") == "1":
            return True
    if getenv("NO_COLOR"):
        return False
    if getenv("FORCE_COLOR"):
        return True

    if sys.platform == "win32":
        try:
            import nt
            if not nt._supports_virtual_terminal():  # noqa
                return False
        except (ImportError, AttributeError):
            return False

    return is_term(file)
