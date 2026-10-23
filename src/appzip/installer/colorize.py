import os
import sys
from dataclasses import dataclass, fields

COLORIZE = True


class SGR:
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"
    ITALIC = "\x1b[3m"
    UNDERLINE = "\x1b[4m"
    BLINK = "\x1b[5m"
    REVERSE = "\x1b[7m"
    STRIKE = "\x1b[9m"
    DEFAULT_FG = "\x1b[39m"
    DEFAULT_BG = "\x1b[49m"

    BLACK = "\x1b[30m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    BLUE = "\x1b[34m"
    MAGENTA = "\x1b[35m"
    CYAN = "\x1b[36m"
    LIGHT_GRAY = "\x1b[37m"

    DARK_GRAY = "\x1b[90m"
    LIGHT_RED = "\x1b[91m"
    LIGHT_GREEN = "\x1b[92m"
    LIGHT_YELLOW = "\x1b[93m"
    LIGHT_BLUE = "\x1b[94m"
    LIGHT_MAGENTA = "\x1b[95m"
    LIGHT_CYAN = "\x1b[96m"
    WHITE = "\x1b[97m"

    BG_BLACK = "\x1b[40m"
    BG_RED = "\x1b[41m"
    BG_GREEN = "\x1b[42m"
    BG_YELLOW = "\x1b[43m"
    BG_BLUE = "\x1b[44m"
    BG_MAGENTA = "\x1b[45m"
    BG_CYAN = "\x1b[46m"
    BG_LIGHT_GRAY = "\x1b[47m"

    BG_DARK_GRAY = "\x1b[100m"
    BG_LIGHT_RED = "\x1b[101m"
    BG_LIGHT_GREEN = "\x1b[102m"
    BG_LIGHT_YELLOW = "\x1b[103m"
    BG_LIGHT_BLUE = "\x1b[104m"
    BG_LIGHT_MAGENTA = "\x1b[105m"
    BG_LIGHT_CYAN = "\x1b[106m"
    BG_WHITE = "\x1b[107m"


def decolor(text: str) -> str:
    """Remove ANSI codes from a string."""
    for attr, code in vars(SGR).items():
        if not attr.startswith("__"):
            text.replace(code, "")
    return text


def can_colorize(file=None) -> bool:
    def _safe_getenv(k: str, fallback: str | None = None) -> str | None:
        try:
            return os.environ.get(k, fallback)
        except Exception:  # noqa
            return fallback

    if file is None:
        file = sys.stdout

    if not sys.flags.ignore_environment:
        if _safe_getenv("PYTHON_COLORS") == "0":
            return False
        if _safe_getenv("PYTHON_COLORS") == "1":
            return True
    if _safe_getenv("NO_COLOR"):
        return False
    if not COLORIZE:
        return False
    if _safe_getenv("FORCE_COLOR"):
        return True
    if _safe_getenv("TERM") == "dumb":
        return False

    if not hasattr(file, "fileno"):
        return False

    if sys.platform == "win32":
        try:
            import nt  # noqa
            if not nt._supports_virtual_terminal():  # noqa
                return False
        except (ImportError, AttributeError):
            return False

    try:
        return os.isatty(file.fileno())
    except OSError:
        return hasattr(file, "isatty") and file.isatty()


@dataclass
class Theme:
    reset: str = SGR.RESET
    # Logging.
    log_time: str = SGR.DIM + SGR.CYAN
    log_debug: str = SGR.BLUE
    log_info: str = SGR.GREEN
    log_warning: str = SGR.LIGHT_YELLOW
    log_error: str = SGR.BOLD + SGR.LIGHT_RED
    log_critical: str = SGR.BOLD + SGR.LIGHT_RED + SGR.REVERSE

    @classmethod
    def no_colors(cls):
        return cls(**{f.name: "" for f in fields(cls)})


def get_theme(file=None) -> Theme:
    return Theme() if can_colorize(file) else Theme.no_colors()
