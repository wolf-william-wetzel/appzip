import logging
from contextlib import contextmanager

from .colorize import get_theme, is_term, decolor
from .pretty import prepr


class ThemeFormatter(logging.Formatter):
    def __init__(self, theme):
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

    @staticmethod
    def prepr(value) -> str:
        return prepr(value).replace("\n", "\n" + " " * 24)

    def format(self, record) -> str:
        # Style the log level name.
        if (level := record.levelname) in self.log_level_styles:
            record.levelname = f"{self.log_level_styles[level]}{level:<8}{self.theme.reset}"
        # Format the message.
        if not isinstance(record.msg, str):
            record.msg = self.prepr(record.msg)
        # Format the args.
        if record.args:
            if isinstance(record.args, tuple):
                record.msg %= tuple(self.prepr(a) for a in record.args)
            else:
                record.msg %= {k: self.prepr(v) for k, v in record.args.items()}
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
    def __init__(self, file=None, interactive: bool | None = None):
        """If ``file`` is ``None``, default to ``sys.stdout``."""
        self.file = file
        self.theme = get_theme(file)
        self.interactive = is_term(file) if interactive is None else interactive
        self.live = Live(self)

    def write(self, value):
        with self.live:
            return self.file.write(value)

    def flush(self):
        return self.file.flush()

    @contextmanager
    def status(self, text, transient: bool = True):
        self.live.update(text)
        try:
            yield self.live
        finally:
            self.live.end(transient)
            self.live.update("")

    def get_logging_handler(self):
        handler = logging.StreamHandler(self)
        handler.setFormatter(ThemeFormatter(self.theme))
        return handler

    def print(self, *values, sep: str = " ", end: str = "\n"):
        """Prints ``values`` styled with rich-like markup."""
        value = sep.join(v if isinstance(v, str) else prepr(v) for v in values)
        with self.live:
            print(self.theme.style(value), end=end, file=self.file)

    def exit(self, message: str, code: int = 1):
        """Print a styled message, then raise ``SystemExit(code)``."""
        self.print(message)
        raise SystemExit(code)
