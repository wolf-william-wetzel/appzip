from pathlib import Path
from typing import Annotated
from importlib.metadata import version, PackageNotFoundError
import logging
from enum import StrEnum
import os
import shutil
from functools import cache
import time
import datetime as dt

import typer
from typer.rich_utils import STYLE_OPTION_ENVVAR, STYLE_OPTION_DEFAULT
import msgspec
from rich.console import Console
from rich.logging import RichHandler
from rich.pretty import pretty_repr

from .config import load_config
from .packer import copy_app

START_TIME = time.perf_counter_ns()


class LogLevel(StrEnum):
    NONE = "NONE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


log = logging.getLogger()
logging.basicConfig(level=LogLevel.DEBUG, handlers=[])
LOG_READY = False

console = Console(highlight=False)

app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
)


@cache
def make_rel(path: str | Path) -> str:
    """If ``path`` is relative to cwd, return ``path`` relative to cwd. Otherwise, return ``path``."""
    path, cwd = Path(path), Path.cwd()
    if path.is_relative_to(cwd):
        return f".{os.path.sep}{path.relative_to(cwd)}"
    return str(path)


@cache
def link(path: str | Path, text: str = "") -> str:
    """Return rich markup linking ``text`` to ``path``.

    If ``text`` isn't given, it will be ``path`` or an equivalent path relative to cwd.
    """
    return f"[link={path}]{text if text else make_rel(path)}[/]"


REPO_LINK = "https://github.com/wolf-william-wetzel/appzip"
EPILOG = f"""This software is free and open source.
[blue][link={REPO_LINK}]{REPO_LINK}[/][/]"""

LOG_HELP_TEXT = (
    "Show logs in console. "
    fr"If env var [{STYLE_OPTION_ENVVAR}]\[DEBUG][/] is set, "
    fr"default to [{STYLE_OPTION_DEFAULT}]\[DEBUG][/]."
)

CONFIG_FILE_NAMES = (
    "appzip.toml",
    "pyproject.toml",
)

ERROR_TEXT = """[red]{msg}
[bold]{exc}[/bold][/red]
[magenta]{suggestion}[/magenta]"""


def throw_error(msg: str, exc: BaseException, suggestion: str = ""):
    """Display user-friendly errors."""
    console.print(ERROR_TEXT.format(msg=msg, exc=exc, suggestion=suggestion))
    if LOG_READY: log.exception(msg, exc_info=exc)
    raise typer.Exit(1) from None


def show_version(value: bool):
    """Display app version."""
    if value:
        try:
            console.print(f"[bold cyan]{version("appzip")}[/]")
        except PackageNotFoundError:
            console.print("[bold red]No version info found.[/]")
        raise typer.Exit()


def find_config(path: Path) -> Path:
    """Search ``path`` for a config file and return it.

    If ``path`` is a file, return it.
    """
    if path.is_file():
        return path
    for config in (path / name for name in CONFIG_FILE_NAMES):
        if config.exists() and os.access(config, os.R_OK):
            return config
    names = ", ".join("'{}'".format(name) for name in CONFIG_FILE_NAMES)
    raise typer.BadParameter(f"{path} contains no readable file matching {names}.")


@app.command(epilog=EPILOG)
def main(
        path: Annotated[Path,
        typer.Argument(
            default_factory=Path.cwd,
            show_default=".",
            exists=True,
            resolve_path=True,
            help="Path to [green]config file[/] or directory containing [green]config file[/].",
            callback=find_config,
        )],
        log_level: Annotated[LogLevel,
        typer.Option(
            "-l", "--log",
            help=LOG_HELP_TEXT,
            show_default="NONE or DEBUG",
            envvar=["APPZIP_LOGLEVEL", "LOGLEVEL", "LOG_LEVEL"],
            case_sensitive=False,
        )] = LogLevel.DEBUG if os.environ.get("DEBUG") else LogLevel.NONE,
        _: Annotated[bool,
        typer.Option(
            "-v", "--version",
            callback=show_version,
            is_eager=True,
            help="Show version number and exit.",
        )] = False,
    ):
    """
    Pack a python app into a cross-platform zip file.
    """
    # Load the configuration.
    with console.status(f"Loading configuration"):
        try:
            config = load_config(path)
        except msgspec.ValidationError as exc:
            throw_error(f"{link(path)} is not a valid config file", exc,
                        "Fix the above issue and try again.")
        except msgspec.DecodeError as exc:
            throw_error(f"{link(path)} cannot be decoded", exc,
                        "Ensure the file is a valid TOML document.")

    # Set up file logging.
    log_file = config.build_dir / "build.log"
    file_handler = logging.FileHandler(
        log_file,
        mode="w",
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s.%(msecs)d %(filename)s:%(lineno)d:%(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    log.addHandler(file_handler)
    # Set up console logging.
    if log_level is not LogLevel.NONE:
        rich_handler = RichHandler(
            level=log_level.value,
            console=console,
            rich_tracebacks=True,
            log_time_format="[%H:%M:%S]",
            show_path=False,
        )
        rich_handler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(rich_handler)

    # Log details.
    global LOG_READY
    LOG_READY = True
    log.info(f"Log file: {make_rel(log_file)}")
    log.info(f"Config file: {make_rel(path)}")
    log.debug(pretty_repr(config, indent_size=2))

    # Get the build directory.
    installer_name = f"{config.name}_{config.version}_installer"
    dest_dir = config.build_dir / installer_name
    # Clear the build directory.
    if dest_dir.exists():
        shutil.rmtree(dest_dir,
                      onexc=lambda _, name, err:
                      throw_error(f"{make_rel(name)} cannot be deleted", err,
                                  f"Clear all files from {link(dest_dir)}"))
    # Copy the project files.
    log.info(f"Copying files to {make_rel(dest_dir)}")
    with console.status("Copying files"):
        copy_app(config.base_dir, dest_dir, config.include, config.exclude)
    log.info(f"Copying complete")
    # Print exit message.
    runtime = dt.timedelta(microseconds=(time.perf_counter_ns() - START_TIME) / 1000)
    console.print(f"[dim]Process completed in [cyan]{runtime}[/][/]")
    console.print(f"Packed project: {link(config.dist_dir / (installer_name + ".pyz"))}")
