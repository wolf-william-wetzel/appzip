import logging
import sys
from pathlib import Path
import atexit
try:
    import tkinter.filedialog as fd
except ImportError:
    fd = None

from .colorize import Theme, decolor
from .pretty import prepr
from .utils import can_interact, can_colorize

log = logging.getLogger(__name__)

CONFIRM_YES = " [b][[l_green]Y[fg]/[l_red]n[fg]][/] "
CONFIRM_NO = " [b][[l_green]y[fg]/[l_red]N[fg]][/] "
STATUS_SPINNER = "[f][l_green]\u25cf[/] "


class ThemeFormatter(logging.Formatter):
    def __init__(self, theme: Theme):
        self.theme = theme
        self.log_level_styles = {
            "DEBUG": self.theme.log_debug,
            "INFO": self.theme.log_info,
            "WARNING": self.theme.log_warning,
            "ERROR": self.theme.log_error,
            "CRITICAL": self.theme.log_critical,
        }
        super().__init__(
            fmt="{theme.log_time}[{asctime}.{msecs:0<3.0f}]{theme.reset} {levelname} {message}",
            datefmt="%H:%M:%S",
            style="{",
            defaults={"theme": self.theme},
        )

    def format(self, record) -> str:
        # Style the log level name.
        if (level := record.levelname) in self.log_level_styles:
            record.levelname = f"{self.log_level_styles[level]}{level:<8}{self.theme.reset}"
        # Format the message.
        if not isinstance(record.msg, str):
            record.msg = prepr(record.msg).replace("\n", "\n" + " " * 24)
        # Format the args.
        if record.args:
            if isinstance(record.args, tuple):
                record.msg %= tuple(prepr(a) for a in record.args)
            else:
                record.msg %= {k: prepr(v) for k, v in record.args.items()}
        record.args = None
        # Style the message.
        record.msg = self.theme.style(record.msg)
        # Standard formatting.
        return super().format(record)


class Live:
    def __init__(self, console: Console, text: str = ""):
        self.console = console
        self.anti_text = self.text = ""
        self.update(text)

    def update(self, text: str):
        if not self.console.interactive:
            return
        with self:
            self.text = self.console.theme.style(str(text))
            text_len = len(decolor(self.text))
            self.anti_text = "".join(s * text_len for s in ("\b", " ", "\b"))

    def show(self, text: str):
        print(text, end="", flush=True, file=self.console.file)

    def disp(self):
        self.show(self.text)

    def clear(self):
        self.show(self.anti_text)

    def end(self, transient: bool = True):
        if transient:
            self.clear()
        else:
            print(flush=True, file=self.console.file)

    def __enter__(self):
        if self.text:
            self.clear()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disp()


class Console:
    """Console object for easy terminal styles."""
    def __init__(self, file=sys.stdout):
        self.file = file
        self.colorized, self.interactive = can_colorize(file), can_interact(file)
        self.theme = Theme() if self.colorized else Theme.no_colors()
        # Live object for status display.
        self.live = Live(self)
        # Terminal progress display via OSC 9;4.
        # Set to `indeterminate` and clear on interpreter exit.
        self._term_progress(3)
        atexit.register(self._end_progress)

    def __str__(self) -> str:
        return (f"[name]{self.__class__.__name__}[/][brace]([/]"
                f"[attr]colorized[/]={prepr(self.colorized)}, "
                f"[attr]interactive[/]={prepr(self.interactive)}"
                f"[brace])[/]")

    # ANSI methods.

    def link(self, text, link: str | None = None):
        if not self.colorized:
            return text
        return f"\x1b]8;;{text if link is None else link}\x1b\\{text}\x1b]8;;\x1b\\"

    def _term_progress(self, state: int = 0, percent: int = 0):
        if self.interactive:
            self.print(f"\x1b]9;4;{state};{percent}\x1b\\", end="")

    # Status methods.

    def status(self, text: str):
        if text:
            log.info(text)
        self.live.update(STATUS_SPINNER + text)

    def _end_progress(self):
        self._term_progress(0)
        self.live.update("")

    # Logging methods.

    def write(self, value):
        with self.live:
            return self.file.write(value)

    def flush(self):
        return self.file.flush()

    def get_logging_handler(self):
        handler = logging.StreamHandler(self)
        handler.setFormatter(ThemeFormatter(self.theme))
        return handler

    # Output methods.

    def print(self, *values, sep: str = " ", end: str = "\n"):
        """Prints ``values`` styled with rich-like markup."""
        value = sep.join(v if isinstance(v, str) else prepr(v) for v in values)
        with self.live:
            print(self.theme.style(value), end=end, file=self.file)

    def exit(self, *messages, code: int = 1, exc: bool | None = None):
        """Log and print a styled message, then raise ``SystemExit(code)``."""
        if code:
            pass_exc = sys.exc_info()[0] is not None if exc is None else exc
            log.critical(f"[error]Exiting with code {code}", exc_info=pass_exc)
        self.print(*messages)
        raise SystemExit(code)

    # Input methods.

    def input(self, prompt: str, default: str = "") -> str:
        if not self.interactive:
            return default
        text = self.live.text
        self.live.update("")
        self.print(prompt, end="")
        result = input() or default
        self.live.update(text)
        return result

    def confirm(self, prompt: str, default: bool = False) -> bool:
        return self.input(prompt + (CONFIRM_YES if default else CONFIRM_NO), "ny"[default]).lower() == "y"

    def ask_folder(self, message: str, default: Path) -> Path | None:
        """If not interactive, default is returned. Otherwise, None means cancel."""
        if not self.interactive:
            return default
        path = self.input(message) if fd is None else fd.askdirectory(title=message, initialdir=default)
        return Path(path).expanduser().resolve() if path else None
