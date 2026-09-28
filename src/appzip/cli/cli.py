from pathlib import Path
from typing import Annotated
from importlib.metadata import version, PackageNotFoundError
import logging
from enum import StrEnum
import os

import typer
from rich import print
from rich.logging import RichHandler


class LogLevel(StrEnum):
    NONE = "NONE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


log = logging.getLogger(__name__)
logging.basicConfig(level=LogLevel.DEBUG, handlers=[])

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})

try:
    __version__ = version("appzip")
except PackageNotFoundError:
    __version__ = ""

REPO_LINK = "https://github.com/wolf-william-wetzel/appzip"
EPILOG = f"""This software is free and open source.
[blue][link={REPO_LINK}]{REPO_LINK}[/]"""

CONFIG_FILE_NAMES = (
    "appzip.toml",
    "pyproject.toml",
)


def show_version(value: bool):
    """Display app version."""
    if value:
        print(__version__ or "[red]No version info found.[/]")
        raise typer.Exit()


def find_config(folder: Path) -> Path:
    """Return the path to a config file in ``folder``."""
    for config in (folder / name for name in CONFIG_FILE_NAMES):
        if config.exists() and os.access(config, os.R_OK):
            return config
    names = ", ".join("'{}'".format(name) for name in CONFIG_FILE_NAMES)
    raise typer.BadParameter(f"{folder} does not contain any of {names}.")


def load_config(path: Path):
    """Find and load the config file."""
    # Find the config file.
    if path.is_dir():
        path = find_config(path)
    # Load the config file.
    pass
    # Return the configuration object.
    return path


# noinspection unused-parameter
@app.command(epilog=EPILOG)
def main(
        config: Annotated[Path,
            typer.Argument(
                default_factory=Path.cwd,
                show_default=".",
                exists=True,
                resolve_path=True,
                help="Path to config file or project directory.",
                callback=load_config,
                metavar="path",
            )],
        version_flag: Annotated[bool,
            typer.Option("-v", "--version",
                callback=show_version,
                is_eager=True,
                help="Show app version and exit.",
            )] = False,
        log_level: Annotated[LogLevel,
            typer.Option("-l", "--log",
                help="Show logs in console.",
                envvar=["LOGLEVEL", "LOG_LEVEL"],
                case_sensitive=False,
            )] = LogLevel.NONE,
    ):
    """
    Pack a python app into a cross-platform zip file.
    """
    # Set up logging.
    if log_level is not LogLevel.NONE:
        rich_handler = RichHandler(level=log_level.value,
                                   rich_tracebacks=True,
                                   log_time_format="[%Y-%m-%d %H:%M:%S.%f]",
                                   )
        rich_handler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(rich_handler)
    # Pack the project.
    log.info(config)
