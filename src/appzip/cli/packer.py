import logging
from pathlib import Path, UnsupportedOperation
from annotationlib import get_annotations
import shutil
import time
import zipapp
import datetime as dt
import os
import sys
from functools import partial

import msgspec
from packaging.requirements import Requirement
from rich.highlighter import JSONHighlighter
from rich.pretty import pretty_repr
from rich.console import Console
from rich.progress import Progress
from rich.progress import (
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
    TimeRemainingColumn,
    TaskProgressColumn,
)

from .utils import format_path, format_node, link, CWD
from .config import Config, EntryPoints, load_config
from .errors import *

START_TIME = time.perf_counter_ns()
IS_WIN = sys.platform == "win32"

log = logging.getLogger(__name__)

prepr = partial(pretty_repr, indent_size=2, expand_all=True)

PARENT_PACKAGE = Path(__file__).resolve().parent.parent
INSTALLER_LIB = PARENT_PACKAGE / "installer"
INSTALLER_ENTRY_POINT = f"{INSTALLER_LIB.name}:main"

PROGRESS_COLUMNS = (
    TextColumn("[progress.description]{task.description}"),  # noqa
    BarColumn(),  # noqa
    MofNCompleteColumn(),  # noqa
    TaskProgressColumn(),  # noqa
    TimeRemainingColumn(compact=True, elapsed_when_finished=True),  # noqa
)

CONFIG_NAMES = (
    "appzip.toml",
    "pyproject.toml",
)


def find_config(path: Path) -> Path:
    """Search ``path`` for a config file and return it.

    If ``path`` is a file, return it.
    If no config files are found, return the directory.
    """
    if path.is_file():
        return path
    for config in (path / name for name in CONFIG_NAMES):
        if config.exists() and os.access(config, os.R_OK):
            return config
    return path


def enc_hook(obj):
    type_ = type(obj)
    if type_ is Requirement:
        return str(obj)
    module = "" if type_.__module__ in (None, "builtins") else f"{type_.__module__}."
    raise NotImplementedError(f"unsupported type '{module}{type_.__qualname__}'")


class Metadata(msgspec.Struct):
    """Metadata for the installer."""
    name: str
    version: str
    description: str
    minimum_python: int
    dependencies: list[Requirement]
    entry_points: EntryPoints

    @classmethod
    def from_config(cls, cfg: Config):
        """Initialize metadata from a ``Config`` object."""
        return cls(**{k: getattr(cfg, k) for k in get_annotations(cls) if hasattr(cfg, k)})


def add_installer_resources(cfg: Config):
    """Add the installer resources to the current build."""
    # Copy the installer lib.
    log.info(f"Copying installer lib to {format_path(cfg.dest_dir / INSTALLER_LIB.name)}/")
    INSTALLER_LIB.copy_into(cfg.dest_dir)
    # Write metadata.
    log.info(f"Writing installer metadata to {format_path(cfg.metadata_file)}")
    with open(cfg.metadata_file, "wb") as f:
        metadata = Metadata.from_config(cfg)
        log.debug(prepr(metadata))
        data = msgspec.json.encode(metadata, enc_hook=enc_hook)
        log.debug(data, extra={"highlighter": JSONHighlighter()})  # noqa
        f.write(data)


def clear_previous_build(path: Path):
    """Clear ``path`` with ``shutil.rmtree``. Raise ``RmtreeError`` if any errors occurred."""
    failures: list[tuple[str, BaseException]] = []
    if path.exists():
        log.info(f"Clearing previous build from {format_path(path)}")
        shutil.rmtree(path, onexc=lambda _, n, e: failures.append((n, e)))
    if failures:
        raise RmtreeError(path, failures)


def parents_ok(node: Path, excluded: set[Path]) -> bool:
    """Return ``True`` if all ``node.parents`` are not excluded and not symlinks."""
    return all((p not in excluded and not p.is_symlink()) for p in node.parents)


def scan_dir(folder: Path, include: tuple[str, ...], exclude: tuple[str, ...]) -> set[Path]:
    """Scan ``path`` and return all nodes matching ``include`` and not ``exclude``."""
    included_nodes: set[Path] = set()
    excluded_nodes: set[Path] = set()

    for pattern in include:
        included_nodes.update(folder.glob(pattern, recurse_symlinks=True))
    for pattern in exclude:
        excluded_nodes.update(folder.glob(pattern, recurse_symlinks=True))

    return {n for n in (included_nodes - excluded_nodes - {folder}) if parents_ok(n, excluded_nodes)}


def copy_node(src_dir: Path, dest_dir: Path, src_node: Path):
    dest_node = dest_dir / src_node.relative_to(src_dir)
    node_str = format_node(src_node, src_dir)

    if not dest_node.parent.exists():
        dest_node.parent.mkdir(parents=True, exist_ok=True)

    if src_node.is_symlink():
        real_node = src_node.resolve()
        node_str = format_node(src_node, src_dir, real_node)
        if src_dir not in real_node.parents:
            log.warning(f"Ignored external symlink {node_str}")
            return
        try:
            dest_node.symlink_to(real_node.relative_to(src_node.parent, walk_up=True), real_node.is_dir())
        except UnsupportedOperation:
            SymlinkWarning.warn("Symlink creation is not available on this system.")
            log.exception(f"Cannot create symlink {node_str}")
            return
        except OSError:
            if IS_WIN:
                SymlinkWarning.warn("Symlink creation is not permitted. "
                    "Run as administrator or activate Windows Developer Mode.")
            log.error(f"Cannot create symlink {node_str}", exc_info=not IS_WIN)
            return
    elif src_node.is_dir():
        dest_node.mkdir(exist_ok=True)
        src_mode = src_node.stat().st_mode
        if dest_node.stat().st_mode != src_mode:
            dest_node.chmod(src_mode)
    elif src_node.is_file():
        try:
            dest_node.hardlink_to(src_node)
        except UnsupportedOperation:
            src_node.copy(dest_node, preserve_metadata=True)
    else:
        log.warning(f"Ignored unknown file type {node_str}")
        return
    log.debug(f"Copied {node_str}")


def pack(cfg: Config, console: Console | None = None):
    """Pack the project."""
    if console is None:
        console = Console(quiet=True)

    # Log config details.
    if cfg.path.is_file():
        log.info(f"Config loaded from {format_path(cfg.path)}")
    else:
        log.warning(f"Using default config. No config file found in {format_path(cfg.path)}")
    log.debug(prepr(cfg))
    if not cfg.version:
        log.warning("No version info found in config.")

    # Clear the build directory.
    with console.status("Clearing previous build"):
        clear_previous_build(cfg.dest_dir)

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
        zipapp.create_archive(cfg.dest_dir, cfg.installer_path, main=INSTALLER_ENTRY_POINT)

    # Print exit message.
    runtime = dt.timedelta(microseconds=(time.perf_counter_ns() - START_TIME) / 1000)
    log.debug(f"Finished in {runtime}")
    console.print(f"[finished]Finished in [finished.time]{runtime}[/][/]")
    console.print(f"[installer.text]Installer: [/]"
                  f"[installer.path]{link(cfg.installer_path.parent)}[/]"
                  f"[installer.filename]{link(cfg.installer_path, cfg.installer_path.name)}[/]")


def run(path: Path = CWD):
    """Run appzip on the provided path."""
    global START_TIME
    START_TIME = time.perf_counter_ns()
    pack(load_config(find_config(path.resolve(strict=True))))
