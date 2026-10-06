from pathlib import Path
from typing import Annotated
from importlib.metadata import version, PackageNotFoundError
import logging
from enum import StrEnum
import os

import typer
from typer.rich_utils import STYLE_OPTION_ENVVAR, STYLE_OPTION_DEFAULT
import msgspec
from rich.console import Console
from rich.logging import RichHandler
from rich.pretty import pretty_repr

from .config import load_config


class LogLevel(StrEnum):
    NONE = "NONE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


log = logging.getLogger(__name__)
logging.basicConfig(level=LogLevel.DEBUG, handlers=[])

console = Console()

app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
)

REPO_LINK = "https://github.com/wolf-william-wetzel/appzip"
EPILOG = f"""This software is free and open source.
[blue][link={REPO_LINK}]{REPO_LINK}[/]"""

LOG_HELP_TEXT = (
    "Show logs in console. "
    f"If env var [{STYLE_OPTION_ENVVAR}]\\[DEBUG][/] is set, "
    f"default to [{STYLE_OPTION_DEFAULT}]\\[DEBUG][/]."
)

CONFIG_FILE_NAMES = (
    "appzip.toml",
    "pyproject.toml",
)

CONFIG_ERROR_MSG = """[red][link={path}]{path}[/link] {message}
[bold]{exc}[/bold][/red]
[magenta]{suggestion}[/magenta]"""
DECODE_ERROR_TEXT = ("cannot be decoded", "Ensure the file is a valid TOML document.")
VALIDATE_ERROR_TEXT = ("is not a valid config file", "Fix the above issue and try again.")


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

    def throw_config_error(message: str, suggestion: str):
        """Print error message and exit the program.

        Must be called from an error scope where ``exc`` is an exception object.
        """
        console.print(CONFIG_ERROR_MSG.format(path=path, exc=exc, message=message, suggestion=suggestion))
        raise typer.Exit(1) from None

    # Load the configuration.
    with console.status(f"Loading config from {path}"):
        try:
            config = load_config(path)
        except msgspec.ValidationError as exc:
            throw_config_error(*VALIDATE_ERROR_TEXT)
        except msgspec.DecodeError as exc:
            throw_config_error(*DECODE_ERROR_TEXT)
        else:
            console.print(f"Loaded config from [link={path}]{path}[/]")
    # Set up logging.
    if log_level is not LogLevel.NONE:
        rich_handler = RichHandler(level=log_level.value,
                                   console=console,
                                   rich_tracebacks=True,
                                   log_time_format="[%Y-%m-%d %H:%M:%S.%f]",
                                   )
        rich_handler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(rich_handler)
    # Pack the project.
    log.info(f"Config path: {path}")
    log.debug(f"Config: {pretty_repr(config, indent_size=2)}")
