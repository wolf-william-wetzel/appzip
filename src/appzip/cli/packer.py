import logging
from pathlib import Path, UnsupportedOperation

from .utils import format_node, IS_WIN, SymlinkWarning


log = logging.getLogger(__name__)


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
            log.error(f"Cannot create symlink {node_str}")
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
