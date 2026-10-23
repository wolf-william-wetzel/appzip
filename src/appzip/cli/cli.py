from pathlib import Path
from typing import Annotated
from importlib.metadata import version, PackageNotFoundError
import logging
from enum import StrEnum
import os

import typer
from typer.rich_utils import STYLE_OPTION_ENVVAR, STYLE_OPTION_DEFAULT
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

from .config import CONFIG_NAMES, Config
from .packer import pack
from .utils import CWD, Format
from .errors import *


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    DEFAULT = WARNING  # The default logging level for this application.


log = logging.getLogger()
logging.basicConfig(level=LogLevel.DEBUG, handlers=[logging.NullHandler()])


def add_handler(handler: logging.Handler, fmt: str, datefmt: str | None = None):
    """Add ``handler`` with formatting to logger."""
    handler.setFormatter(logging.Formatter(fmt, datefmt))
    log.addHandler(handler)


theme = Theme({
    # Change bar themes to ANSI colors.
    "bar.back": "dim bright_black",  # 'dim' style disabled during pulse animation.
    "bar.complete": "bright_green",  # In-progress.
    "bar.finished": "green",  # Progress actually finished.
    "bar.pulse": "bright_green",
    # Modify other defaults.
    "progress.percentage": "bright_green",  # Fits better with the new ANSI bar colors.
    "repr.path": "magenta",  # Same as default.
    "repr.filename": "bright_magenta",  # Same as default.
    "logging.keyword": "magenta",  # Same as 'repr.path'.
    "logging.level.warning": "bright_yellow",  # Use bright version of color.
    "logging.level.error": "bold bright_red",  # Use bright version of color.
    "logging.level.critical": "reverse bold bright_red",  # Use bright version of color.
    # Custom styles.
    # 'installer': exit message about path to installer
    "installer.text": "default",
    "installer.path": "yellow",
    "installer.filename": "bright_yellow",
    # 'finished': exit message about elapsed time
    "finished": "dim",
    "finished.time": "cyan",
    # 'version': version info CLI option
    "version.number": "bold cyan",
    "version.error": "bold red",
    # 'error': exception display
    "error.msg": "red",
    "error.exc": "red bold",
    "error.suggestion": "magenta",
    # 'help' & 'config': help messages
    "help.url": "bright_blue",
    "help.envvar": STYLE_OPTION_ENVVAR,
    "help.default": STYLE_OPTION_DEFAULT,
    "config": "dim bold green",
    "config.name": "bright_green",
})
# Style for typer console when requesting nonexistent style.
MISSING_STYLE = "bold italic blink bright_magenta"  # Make it really obvious something's wrong.

console = Console(
    highlight=False,
    theme=theme,
)

app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
)


def style(style_str: str):
    """Return rich markup tag for ``style_str``, or ``MISSING_STYLE`` if invalid."""
    return f"[{theme.styles.get(style_str) or MISSING_STYLE}]"


REPO_LINK = "https://github.com/wolf-william-wetzel/appzip"
EPILOG = f"""This software is free and open source.
{style("help.url")}{Format.link(REPO_LINK, REPO_LINK)}[/]"""

DEBUG_ENV_VAR = "DEBUG"
LOG_HELP_TEXT = f"""Filter logs by severity.
If env var {style("help.envvar")}{DEBUG_ENV_VAR}[/] is set,
change default from {style("help.default")}{LogLevel.DEFAULT!s}[/]
to {style("help.default")}{LogLevel.DEBUG!s}[/]."""

CONFIG_NAMES_STR = f"{style("config")}|[/]".join(f"{style("config.name")}{name}[/]" for name in CONFIG_NAMES)

PATH_HELP_TEXT = f"""Config file or project directory.
If directory, use default config unless it contains one of
{style("config")}([/]{CONFIG_NAMES_STR}{style("config")})[/]."""

ERROR_TEXT = """[error.msg]{msg}[/]
[error.exc]{exc}[/]
[error.suggestion]{suggestion}[/]"""


def throw_error(msg: str, exc: BaseException, suggestion: str = ""):
    """Display user-friendly errors."""
    log.critical(msg, exc_info=exc)
    console.print(ERROR_TEXT.format(msg=msg, exc=exc, suggestion=suggestion))
    raise typer.Exit(1) from None


def show_version(value: bool):
    """Display app version."""
    if value:
        try:
            console.print(f"[version.number]{version("appzip")}[/]")
        except PackageNotFoundError:
            console.print("[version.error]No version info found.[/]")
        raise typer.Exit()


@app.command(epilog=EPILOG)
def main(
        path: Annotated[Path,
        typer.Argument(
            show_default=".",
            exists=True,
            resolve_path=True,
            help=PATH_HELP_TEXT,
        )] = CWD,
        log_level: Annotated[LogLevel,
        typer.Option(
            "-l", "--log",
            help=LOG_HELP_TEXT,
            show_default=f"{LogLevel.DEFAULT!s} or {LogLevel.DEBUG!s}",
            envvar=["APPZIP_LOGLEVEL", "LOGLEVEL", "LOG_LEVEL"],
            case_sensitive=False,
        )] = LogLevel.DEBUG if os.environ.get(DEBUG_ENV_VAR) else LogLevel.DEFAULT,
        _: Annotated[bool,
        typer.Option(
            "-v", "--version",
            callback=show_version,
            is_eager=True,
            help="Show version number and exit.",
        )] = False,
    ):
    """
    Pack a python app into a cross-platform executable zip file. [bold]:snake:->:package:->:computer:[/]
    """
    # Load the configuration.
    with console.status("Loading configuration"):
        try:
            cfg = Config.load(path)
        except ValidationError as exc:
            throw_error(f"{Format.link(path)} is not a valid config path", exc,
                        "Fix the above issue and try again.")
        except DecodeError as exc:
            throw_error(f"{Format.link(path)} cannot be decoded", exc,
                        "Ensure the file is a valid TOML document.")

    # Set up file logging.
    add_handler(
        logging.FileHandler(
            cfg.log_file,
            mode="w",
            encoding="utf-8"
        ),
        "%(asctime)s.%(msecs)d %(filename)s:%(lineno)d:%(levelname)s %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )
    # Set up console logging.
    add_handler(
        RichHandler(
            level=log_level.value,
            console=console,
            rich_tracebacks=True,
            log_time_format="[%H:%M:%S.%f]",
            show_path=False,
            keywords=[f" {g}/" for g in Format.glyphs.values()],
        ),
        "%(message)s"
    )

    # Pack the project.
    try:
        pack(cfg, console)
    except RmtreeError as exc:
        throw_error(f"Cannot delete the following files from {Format.path(cfg.dest_dir)}", exc,
                    f"Clear all files from {Format.link(cfg.dest_dir)}")
