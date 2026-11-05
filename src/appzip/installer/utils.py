import os
import sys
import logging


def getenv(var: str, fallback: str = "") -> str:
    try:
        return os.environ.get(var, fallback)
    except Exception:  # noqa
        return fallback

LOG_LEVELS = logging.getLevelNamesMapping()
LOG_LEVELS.pop("CRITICAL")
LOG_LEVELS.pop("WARNING")
LOG_LEVELS.pop("NOTSET")

LOG_LEVEL = (getenv("LOGLEVEL") or getenv("LOG_LEVEL")).upper()
LOG_LEVEL = {"CRITICAL": "FATAL", "WARNING": "WARN"}.get(LOG_LEVEL, LOG_LEVEL)
if LOG_LEVEL not in LOG_LEVELS:
    LOG_LEVEL = "DEBUG" if getenv("DEBUG") else "WARN"

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
