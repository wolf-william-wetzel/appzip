import os
import sys
from dataclasses import dataclass, fields


class SGR:
    RESET = "\x1b[0m"

    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"
    ITALIC = "\x1b[3m"
    UNDERLINE = "\x1b[4m"
    BLINK = "\x1b[5m"
    REVERSE = "\x1b[7m"
    STRIKE = "\x1b[9m"

    NOT_BOLD = "\x1b[22m"
    NOT_DIM = "\x1b[22m"
    NOT_ITALIC = "\x1b[23m"
    NOT_UNDERLINE = "\x1b[24m"
    NOT_BLINK = "\x1b[25m"
    NOT_REVERSE = "\x1b[27m"
    NOT_STRIKE = "\x1b[29m"

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


def _safe_getenv(k: str, fallback: str | None = None) -> str | None:
    """Copied from the Python 3.15 stdlib with some modifications."""
    try:
        return os.environ.get(k, fallback)
    except Exception:  # noqa
        return fallback


def is_term(file=None) -> bool:
    """Copied from the Python 3.15 stdlib with some modifications."""
    if file is None:
        file = sys.stdout

    if _safe_getenv("TERM") in ("dumb", "unknown"):
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


def can_colorize(file=None) -> bool:
    """Copied from the Python 3.15 stdlib with some modifications."""
    if not sys.flags.ignore_environment:
        if _safe_getenv("PYTHON_COLORS") == "0":
            return False
        if _safe_getenv("PYTHON_COLORS") == "1":
            return True
    if _safe_getenv("NO_COLOR"):
        return False
    if _safe_getenv("FORCE_COLOR"):
        return True

    if sys.platform == "win32":
        try:
            import nt  # noqa
            if not nt._supports_virtual_terminal():  # noqa
                return False
        except (ImportError, AttributeError):
            return False

    return is_term(file)


@dataclass
class Theme:
    reset: str = SGR.RESET
    # Standard styles.
    bold: str = SGR.BOLD
    dim: str = SGR.DIM
    italic: str = SGR.ITALIC
    underline: str = SGR.UNDERLINE
    blink: str = SGR.BLINK
    reverse: str = SGR.REVERSE
    strike: str = SGR.STRIKE
    # Reverse styles.
    not_bold: str = SGR.NOT_BOLD
    not_dim: str = SGR.NOT_DIM
    not_italic: str = SGR.NOT_ITALIC
    not_underline: str = SGR.NOT_UNDERLINE
    not_blink: str = SGR.NOT_BLINK
    not_reverse: str = SGR.NOT_REVERSE
    not_strike: str = SGR.NOT_STRIKE
    # Defaults.
    fg: str = SGR.DEFAULT_FG
    bg: str = SGR.DEFAULT_BG
    # Standard colors.
    black: str = SGR.BLACK
    red: str = SGR.RED
    green: str = SGR.GREEN
    yellow: str = SGR.YELLOW
    blue: str = SGR.BLUE
    magenta: str = SGR.MAGENTA
    cyan: str = SGR.CYAN
    l_gray: str = SGR.LIGHT_GRAY
    # Bright colors.
    gray: str = SGR.DARK_GRAY
    l_red: str = SGR.LIGHT_RED
    l_green: str = SGR.LIGHT_GREEN
    l_yellow: str = SGR.LIGHT_YELLOW
    l_blue: str = SGR.LIGHT_BLUE
    l_magenta: str = SGR.LIGHT_MAGENTA
    l_cyan: str = SGR.LIGHT_CYAN
    white: str = SGR.WHITE
    # Background colors.
    black_bg: str = SGR.BG_BLACK
    red_bg: str = SGR.BG_RED
    green_bg: str = SGR.BG_GREEN
    yellow_bg: str = SGR.BG_YELLOW
    blue_bg: str = SGR.BG_BLUE
    magenta_bg: str = SGR.BG_MAGENTA
    cyan_bg: str = SGR.BG_CYAN
    l_gray_bg: str = SGR.BG_LIGHT_GRAY
    # Bright background colors.
    gray_bg: str = SGR.BG_DARK_GRAY
    l_red_bg: str = SGR.BG_LIGHT_RED
    l_green_bg: str = SGR.BG_LIGHT_GREEN
    l_yellow_bg: str = SGR.BG_LIGHT_YELLOW
    l_blue_bg: str = SGR.BG_LIGHT_BLUE
    l_magenta_bg: str = SGR.BG_LIGHT_MAGENTA
    l_cyan_bg: str = SGR.BG_LIGHT_CYAN
    white_bg: str = SGR.BG_WHITE
    # Logging.
    log_time: str = SGR.DIM + SGR.CYAN
    log_debug: str = SGR.GREEN
    log_info: str = SGR.BLUE
    log_warning: str = SGR.LIGHT_YELLOW
    log_error: str = SGR.BOLD + SGR.LIGHT_RED
    log_critical: str = SGR.BOLD + SGR.WHITE + SGR.BG_RED
    # Repr.
    string: str = SGR.GREEN
    number: str = SGR.CYAN + SGR.BOLD
    error: str = SGR.RED + SGR.BOLD
    time: str = SGR.LIGHT_GREEN + SGR.BOLD
    true: str = SGR.LIGHT_GREEN + SGR.ITALIC
    false: str = SGR.LIGHT_RED + SGR.ITALIC
    none: str = SGR.MAGENTA + SGR.ITALIC
    brace: str = SGR.BOLD
    name: str = SGR.BOLD + SGR.MAGENTA
    attr: str = SGR.YELLOW
    bytes: str = SGR.LIGHT_GREEN
    ellipsis: str = SGR.YELLOW
    indent: str = SGR.GREEN + SGR.DIM
    path: str = SGR.MAGENTA
    filename: str = SGR.LIGHT_MAGENTA
    notimpl: str = SGR.ITALIC + SGR.RED
    dataclass: str = SGR.LIGHT_YELLOW + SGR.ITALIC
    hint: str = SGR.CYAN
    default: str = SGR.RESET
    doc: str = SGR.DIM + SGR.ITALIC + SGR.GREEN
    app: str = SGR.LIGHT_CYAN
    version: str = SGR.BOLD + SGR.CYAN
    link: str = SGR.LIGHT_BLUE

    @classmethod
    def no_colors(cls):
        return cls(**{f.name: "" for f in fields(cls)})

    def style(self, text: str, reset: bool = True) -> str:
        """Style ``text`` with rich-like markup."""
        if not text: return text
        for f in fields(self):
            text = text.replace(f"[{f.name}]", getattr(self, f.name))
        return text.replace("[/]", self.reset) + (self.reset if reset else "")


def get_theme(file=None) -> Theme:
    """Get a styled or non-styled Theme object. ``file`` defaults to ``sys.stdout``."""
    return Theme() if can_colorize(file) else Theme.no_colors()
