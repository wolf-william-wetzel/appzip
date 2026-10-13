import logging
from pathlib import Path, UnsupportedOperation

from .utils import format_path, CWD, HOME


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
    real_node = None

    def format_node() -> str:
        return (f"{format_path(src_node, (src_dir,))}"
                f"{'' if real_node is None else
                f' -> {format_path(real_node, (src_dir, CWD, HOME))}'}")

    if not dest_node.parent.exists():
        dest_node.parent.mkdir(parents=True, exist_ok=True)

    if src_node.is_symlink():
        real_node = src_node.resolve()
        is_dir = real_node.is_dir()
        if src_dir not in real_node.parents:
            log.warning(f"Ignored external symlink {format_node()}")
            return
        dest_node.symlink_to(real_node.relative_to(src_node.parent, walk_up=True), is_dir)
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
        log.warning(f"Ignored unknown file type {format_node()}")
        return
    log.debug(f"Copied {format_node()}")
