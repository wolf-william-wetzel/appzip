from pathlib import Path
from typing import Annotated
from importlib.metadata import version, PackageNotFoundError

import typer
from rich import print

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})

try:
    __version__ = version("appzip")
except PackageNotFoundError:
    __version__ = ""

REPO_LINK = "https://github.com/wolf-william-wetzel/appzip"
EPILOG = f"""This software is free and open source.
[blue][link={REPO_LINK}]{REPO_LINK}[/]"""


def version_callback(value: bool):
    """Display app version."""
    if value:
        print(__version__ or "[red]No version info found.[/]")
        raise typer.Exit()


# noinspection unused-parameter
@app.command(epilog=EPILOG)
def main(
        path: Annotated[Path,
            typer.Argument(default_factory=Path.cwd,
                           show_default="current working directory",
                           exists=True,
                           resolve_path=True,
                           help="Path to config file or project directory.",
                           )],
        show_version: Annotated[bool,
            typer.Option("-v", "--version",
                         callback=version_callback,
                         is_eager=True,
                         help="Show app version and exit.",
                         )] = False,
    ):
    """
    Pack the given project into a distributable zip file.
    """
    print(path)
