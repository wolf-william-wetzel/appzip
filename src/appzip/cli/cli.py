from pathlib import Path
from typing import Annotated
from importlib.metadata import version, PackageNotFoundError
import logging
from enum import StrEnum
import os
import shutil

import typer
from typer.rich_utils import STYLE_OPTION_ENVVAR, STYLE_OPTION_DEFAULT
import msgspec
from rich.console import Console
from rich.logging import RichHandler
from rich.pretty import pretty_repr

from .config import load_config
from .packer import copy_app


class LogLevel(StrEnum):
    NONE = "NONE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


log = logging.getLogger()
logging.basicConfig(level=LogLevel.DEBUG, handlers=[])

console = Console()

app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
)

LINK_STR = "[link={0}]{0}[/]"

REPO_LINK = "https://github.com/wolf-william-wetzel/appzip"
EPILOG = f"""This software is free and open source.
[blue]{LINK_STR.format(REPO_LINK)}[/]"""

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
    raise typer.Exit(1) from None


def show_version(value: bool):
    """Display app version."""
    if value:
        try:
            console.print(version("appzip"))
        except PackageNotFoundError:
            console.print("[red]No version info found.[/]")
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
    path_str = LINK_STR.format(path)
    with console.status(f"Loading config from {path}"):
        try:
            config = load_config(path)
        except msgspec.ValidationError as exc:
            throw_error(f"{path_str} is not a valid config file", exc,
                        "Fix the above issue and try again.")
        except msgspec.DecodeError as exc:
            throw_error(f"{path_str} cannot be decoded", exc,
                        "Ensure the file is a valid TOML document.")
        else:
            console.print(f"Loaded config from {path_str}")

    # Set up file logging.
    file_handler = logging.FileHandler(
        config.build_dir / "build.log",
        mode="w",
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s.%(msecs)d %(levelname)s:%(filename)s:%(lineno)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    log.addHandler(file_handler)
    # Set up console logging.
    if log_level is not LogLevel.NONE:
        rich_handler = RichHandler(
            level=log_level.value,
            console=console,
            rich_tracebacks=True,
            log_time_format="[%Y-%m-%d %H:%M:%S.%f]",
        )
        rich_handler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(rich_handler)
    # Log details.
    log.info(f"Config path: {path}")
    log.info(pretty_repr(config, indent_size=2))

    # Get the build directory.
    installer_name = f"{config.name}_{config.version}_installer"
    dest_dir = config.build_dir / installer_name
    # Clear the build directory.
    if dest_dir.exists():
        shutil.rmtree(dest_dir,
                      onexc=lambda _, name, err:
                      throw_error(f"{LINK_STR.format(name)} cannot be deleted", err,
                                  f"Clear all files from {LINK_STR.format(dest_dir)}"))
    # Copy the app.
    with console.status("Copying files"):
        copy_app(config.base_dir, dest_dir, config.include, config.exclude)
    console.print(f"Files copied into {LINK_STR.format(dest_dir)}")
    log.info(f"Files copied: {dest_dir}")
