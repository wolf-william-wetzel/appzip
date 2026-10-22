from pathlib import Path
from typing import Annotated
from importlib.metadata import version, PackageNotFoundError
import logging
from enum import StrEnum
import os
import time
import datetime as dt
import zipapp

import typer
from typer.rich_utils import STYLE_OPTION_ENVVAR, STYLE_OPTION_DEFAULT
from msgspec import ValidationError, DecodeError
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
    TimeRemainingColumn,
    TaskProgressColumn,
)

from .config import load_config
from .packer import scan_dir, copy_node, add_installer_resources, clear_previous_build
from .utils import format_path, link, CWD, path_abbrev, prepr, RmtreeError

START_TIME = time.perf_counter_ns()


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


PROGRESS_COLUMNS = (
    TextColumn("[progress.description]{task.description}"),  # noqa
    BarColumn(),  # noqa
    MofNCompleteColumn(),  # noqa
    TaskProgressColumn(),  # noqa
    TimeRemainingColumn(compact=True, elapsed_when_finished=True),  # noqa
)

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
{style("help.url")}{link(REPO_LINK, REPO_LINK)}[/]"""

DEBUG_ENV_VAR = "DEBUG"
LOG_HELP_TEXT = f"""Filter logs by severity.
If env var {style("help.envvar")}{DEBUG_ENV_VAR}[/] is set,
change default from {style("help.default")}{LogLevel.DEFAULT!s}[/]
to {style("help.default")}{LogLevel.DEBUG!s}[/]."""


CONFIG_NAMES = (
    "appzip.toml",
    "pyproject.toml",
)

CONFIG_NAMES_STR = f"{style("config")}|[/]".join(f"{style("config.name")}{name}[/]" for name in CONFIG_NAMES)

PATH_HELP_TEXT = f"""The config file or a directory.
If it's a directory, it must contain one of
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


def find_config(path: Path) -> Path:
    """Search ``path`` for a config file and return it.

    If ``path`` is a file, return it.
    """
    if path.is_file():
        return path
    for config in (path / name for name in CONFIG_NAMES):
        if config.exists() and os.access(config, os.R_OK):
            return config
    names = ", ".join(f"'{name}'" for name in CONFIG_NAMES)
    raise typer.BadParameter(f"'{format_path(path)}' contains no readable file matching {names}.")


@app.command(epilog=EPILOG)
def main(
        config_path: Annotated[Path,
        typer.Argument(
            show_default=".",
            exists=True,
            resolve_path=True,
            help=PATH_HELP_TEXT,
            callback=find_config,
            metavar="config",
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
    Pack a python app into a cross-platform zip file. [bold]:snake:->:package:->:computer:[/]
    """
    # Load the configuration.
    with console.status("Loading configuration"):
        try:
            cfg = load_config(config_path)
        except ValidationError as exc:
            throw_error(f"{link(config_path)} is not a valid config file", exc,
                        "Fix the above issue and try again.")
        except DecodeError as exc:
            throw_error(f"{link(config_path)} cannot be decoded", exc,
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
            keywords=[f" {abbrev}/" for abbrev in path_abbrev.values()],
        ),
        "%(message)s"
    )

    # Log config details.
    log.info(f"Config loaded from {format_path(config_path)}")
    log.debug(prepr(cfg))

    # Clear the build directory.
    with console.status("Clearing previous build"):
        try:
            clear_previous_build(cfg.dest_dir)
        except RmtreeError as exc:
            throw_error(f"Cannot delete the following files from {format_path(cfg.dest_dir)}", exc,
                        f"Clear all files from {link(cfg.dest_dir)}")

    # Scan the project files.
    log.info(f"Scanning {format_path(cfg.base_dir)}")
    with console.status("Scanning files"):
        nodes = scan_dir(cfg.base_dir, cfg.include, cfg.exclude)

    # Copy the project files.
    log.info(f"Copying {len(nodes)} nodes to {format_path(cfg.app_dir)}")
    with Progress(*PROGRESS_COLUMNS, console=console, transient=True) as progress:
        for node in progress.track(nodes, description="Copying files"):
            copy_node(cfg.base_dir, cfg.app_dir, node)

    # Copy the installer resources.
    log.info(f"Adding installer resources to {format_path(cfg.dest_dir)}")
    with console.status("Adding installer resources"):
        add_installer_resources(cfg)

    # Zip the project.
    log.info(f"Packing installer to {format_path(cfg.installer_path)}")
    with console.status("Packing installer"):
        zipapp.create_archive(cfg.dest_dir, cfg.installer_path)

    # Print exit message.
    runtime = dt.timedelta(microseconds=(time.perf_counter_ns() - START_TIME) / 1000)
    log.debug(f"Finished in {runtime}")
    console.print(f"[finished]Finished in [finished.time]{runtime}[/][/]")
    console.print(f"[installer.text]Installer: [/]"
                  f"[installer.path]{link(cfg.installer_path.parent)}[/]"
                  f"[installer.filename]{link(cfg.installer_path, cfg.installer_path.name)}[/]")
