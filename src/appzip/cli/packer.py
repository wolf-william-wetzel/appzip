import logging
from pathlib import Path, UnsupportedOperation


log = logging.getLogger(__name__)


def posix(path: Path, is_dir: bool = False) -> str:
    """Convert ``path`` to posix format, with a trailing slash for directories."""
    return f"{'' if path.is_absolute() else '.../'}{path.as_posix()}{'/' if is_dir else ''}"


def log_node(msg: str, node: Path, is_dir: bool = False, link: Path | None = None) -> None:
    """Log a debug message along with a formatted node."""
    log.debug(f"{msg}: {posix(node, is_dir)}{'' if link is None else f' -> {posix(link, is_dir)}'}")


def parents_ok(node: Path, excluded: set[Path]) -> bool:
    """Return ``True`` if all ``node.parents`` are not excluded and not symlinks."""
    return all((p not in excluded and not p.is_symlink()) for p in node.parents)


def scan_dir(folder: Path, include: tuple[str, ...], exclude: tuple[str, ...]) -> set[Path]:
    """Scan ``path`` and return all nodes matching ``include`` and not ``exclude``."""
    included_nodes: set[Path] = {folder}
    excluded_nodes: set[Path] = set()

    for pattern in include:
        included_nodes.update(folder.glob(pattern, recurse_symlinks=True))
    for pattern in exclude:
        excluded_nodes.update(folder.glob(pattern, recurse_symlinks=True))

    return {n for n in (included_nodes - excluded_nodes) if parents_ok(n, excluded_nodes)}


def copy_node(src_dir: Path, dest_dir: Path, src_node: Path):
    rel_node = src_node.relative_to(src_dir)
    dest_node = dest_dir / rel_node

    if not dest_node.parent.exists():
        dest_node.parent.mkdir(parents=True, exist_ok=True)

    if src_node.is_symlink():
        real_node = src_node.resolve()
        is_dir = real_node.is_dir()
        if src_dir not in real_node.parents:
            log_node("Ignored external symlink", rel_node, is_dir, real_node)
            return
        dest_node.symlink_to(real_node.relative_to(src_node.parent, walk_up=True), is_dir)
        log_node("Copied", rel_node, is_dir, real_node.relative_to(src_dir))
    elif src_node.is_dir():
        dest_node.mkdir(exist_ok=True)
        src_mode = src_node.stat().st_mode
        if dest_node.stat().st_mode != src_mode:
            dest_node.chmod(src_mode)
        log_node("Copied", rel_node, True)
    elif src_node.is_file():
        try:
            dest_node.hardlink_to(src_node)
        except UnsupportedOperation:
            src_node.copy(dest_node, preserve_metadata=True)
        log_node("Copied", rel_node)
    else:
        log_node("Ignored unknown file type", rel_node)
        return
