from dataclasses import dataclass, fields
from functools import cache

from .utils import can_colorize


@dataclass
class ANSI:
    reset: str = "\x1b[0m"
    # Styles.
    b: str = "\x1b[1m"  # Bold.
    d: str = "\x1b[2m"  # Dim.
    i: str = "\x1b[3m"  # Italic
    u: str = "\x1b[4m"  # Underline.
    f: str = "\x1b[5m"  # Blink.
    r: str = "\x1b[7m"  # Reverse.
    s: str = "\x1b[9m"  # Strikethrough.
    # Disable styles.
    nb: str = "\x1b[22m"  # Also disables dim.
    nd: str = "\x1b[22m"  # Also disables bold.
    ni: str = "\x1b[23m"
    nu: str = "\x1b[24m"
    nf: str = "\x1b[25m"
    nr: str = "\x1b[27m"
    ns: str = "\x1b[29m"
    # Default colors.
    fg: str = "\x1b[39m"
    bg: str = "\x1b[49m"
    # Colors.
    black: str = "\x1b[30m"
    red: str = "\x1b[31m"
    green: str = "\x1b[32m"
    yellow: str = "\x1b[33m"
    blue: str = "\x1b[34m"
    magenta: str = "\x1b[35m"
    cyan: str = "\x1b[36m"
    l_gray: str = "\x1b[37m"
    # Bright colors.
    gray: str = "\x1b[90m"
    l_red: str = "\x1b[91m"
    l_green: str = "\x1b[92m"
    l_yellow: str = "\x1b[93m"
    l_blue: str = "\x1b[94m"
    l_magenta: str = "\x1b[95m"
    l_cyan: str = "\x1b[96m"
    white: str = "\x1b[97m"
    # Background colors.
    black_bg: str = "\x1b[40m"
    red_bg: str = "\x1b[41m"
    green_bg: str = "\x1b[42m"
    yellow_bg: str = "\x1b[43m"
    blue_bg: str = "\x1b[44m"
    magenta_bg: str = "\x1b[45m"
    cyan_bg: str = "\x1b[46m"
    l_gray_bg: str = "\x1b[47m"
    # Bright background colors.
    gray_bg: str = "\x1b[100m"
    l_red_bg: str = "\x1b[101m"
    l_green_bg: str = "\x1b[102m"
    l_yellow_bg: str = "\x1b[103m"
    l_blue_bg: str = "\x1b[104m"
    l_magenta_bg: str = "\x1b[105m"
    l_cyan_bg: str = "\x1b[106m"
    white_bg: str = "\x1b[107m"

    @classmethod
    @cache
    def all_codes(cls) -> set:
        return {f.default for f in fields(cls)}


def decolor(text: str) -> str:
    """Remove ANSI codes from a string."""
    for code in ANSI.all_codes():
        text.replace(code, "")
    return text


@dataclass
class Theme(ANSI):
    # Logging.
    log_time: str = ANSI.d + ANSI.cyan
    log_debug: str = ANSI.green
    log_info: str = ANSI.blue
    log_warning: str = ANSI.l_yellow
    log_error: str = ANSI.b + ANSI.l_red
    log_critical: str = ANSI.b + ANSI.white + ANSI.red_bg
    # Repr.
    string: str = ANSI.green
    number: str = ANSI.cyan + ANSI.b
    error: str = ANSI.red + ANSI.b
    time: str = ANSI.l_green + ANSI.b
    true: str = ANSI.l_green + ANSI.i
    false: str = ANSI.l_red + ANSI.i
    none: str = ANSI.magenta + ANSI.i
    brace: str = ANSI.b
    name: str = ANSI.b + ANSI.magenta
    attr: str = ANSI.yellow
    bytes: str = ANSI.l_green
    ellipsis: str = ANSI.yellow
    indent: str = ANSI.green + ANSI.d
    path: str = ANSI.magenta
    filename: str = ANSI.l_magenta
    notimpl: str = ANSI.i + ANSI.red
    # Output styles.
    app: str = ANSI.l_cyan
    version: str = ANSI.b + ANSI.cyan
    link: str = ANSI.l_blue
    # File trees.
    tree: str = ANSI.magenta + ANSI.d
    file: str = ANSI.yellow
    dir: str = ANSI.l_magenta
    pyfile: str = ANSI.l_blue
    dunder_file: str = ANSI.i
    timestamp: str = ANSI.l_green + ANSI.d
    filesize: str = ANSI.d + ANSI.cyan + ANSI.b
    dotfile: str = ANSI.d
    symlink: str = ANSI.u
    filemode: str = ANSI.d

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
