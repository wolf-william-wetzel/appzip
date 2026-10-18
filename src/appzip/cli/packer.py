import logging
from pathlib import Path, UnsupportedOperation

import msgspec

from .utils import format_path, format_node, IS_WIN, SymlinkWarning
from .config import Config


log = logging.getLogger(__name__)

PARENT_PACKAGE = Path(__file__).resolve().parent.parent
INSTALLER_LIB = PARENT_PACKAGE / "installer"
INSTALLER_ENTRY_POINT = PARENT_PACKAGE / "installer_ep.py"


class Metadata(msgspec.Struct):
    """Metadata for the installer."""
    name: str
    version: str
    description: str = ""
    minimum_python: int = 0
    dependencies: list[str] = []

    @classmethod
    def from_config(cls, cfg: Config):
        """Initialize metadata from a ``Config`` object."""
        min_python = 0
        return cls(cfg.name, cfg.version, cfg.description or "", min_python, cfg.dependencies)

    @classmethod
    def write_config_to_file(cls, cfg: Config):
        """Write metadata initialized from ``cfg`` to ``cfg.metadata_file``."""
        with open(cfg.metadata_file, "wb") as f:
            f.write(msgspec.json.encode(cls.from_config(cfg)))


def add_installer_resources(cfg: Config):
    """Add the installer resources to the current build."""
    # Copy the installer lib.
    log.debug(f"Copying installer lib to {format_path(cfg.dest_dir / INSTALLER_LIB.name, force_dir=True)}")
    INSTALLER_LIB.copy_into(cfg.dest_dir)
    # Copy the installer entry point.
    log.debug(f"Copying installer entry point to {format_path(cfg.entry_point)}")
    INSTALLER_ENTRY_POINT.copy(cfg.entry_point)
    # Write metadata.
    log.debug(f"Writing installer metadata to {format_path(cfg.metadata_file)}")
    Metadata.write_config_to_file(cfg)


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
