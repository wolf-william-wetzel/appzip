import sys
import logging

from .colorize import get_theme


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

    def format(self, record) -> str:
        # Style the log level name.
        if (level := record.levelname) in self.log_level_styles:
            record.levelname = f"{self.log_level_styles[level]}{level}{self.theme.reset}"
        # Style the message.
        record.msg, record.args = self.theme.style(record.getMessage(), reset=True), None
        # Standard formatting.
        return super().format(record)


class Console:
    def __init__(self, file=sys.stdout):
        self.file = file
        self.theme = get_theme(file)

    def get_logging_handler(self):
        handler = logging.StreamHandler(self.file)
        handler.setFormatter(ThemeFormatter(self.theme))
        return handler

    def print(self, text: str, clear_styles: bool = True):
        """Prints ``text`` styled with rich-like markup.

        If ``clear_styles``, styles will be reset at the end of the text.
        """
        print(self.theme.style(text, clear_styles), file=self.file)

    def exit(self, message: str, code: int = 1):
        """Print a styled message, then raise ``SystemExit(code)``."""
        self.print(message)
        raise SystemExit(code)
