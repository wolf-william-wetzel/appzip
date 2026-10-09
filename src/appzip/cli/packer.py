import logging
from pathlib import Path, UnsupportedOperation


log = logging.getLogger()


def parents_ok(node: Path, excluded: set[Path]) -> bool:
    """Return ``True`` if all ``node.parents`` are not excluded and not symlinks."""
    return all((p not in excluded and not p.is_symlink()) for p in node.parents)


def copy_app(src_dir: Path, dest_dir: Path, include: tuple[str, ...], exclude: tuple[str, ...]):
    """Copy the app from ``src_dir`` to ``dest_dir``, respecting the pattern matches."""
    included_nodes: set[Path] = {src_dir}
    excluded_nodes: set[Path] = set()

    for pattern in include:
        included_nodes.update(src_dir.glob(pattern, recurse_symlinks=True))
    for pattern in exclude:
        excluded_nodes.update(src_dir.glob(pattern, recurse_symlinks=True))

    for src_node in (n for n in (included_nodes - excluded_nodes) if parents_ok(n, excluded_nodes)):
        dest_node = dest_dir / src_node.relative_to(src_dir)

        if not dest_node.parent.exists():
            dest_node.parent.mkdir(parents=True, exist_ok=True)

        if src_node.is_symlink():
            real_node = src_node.resolve()
            if src_dir not in real_node.parents:
                log.debug(f"External symlink, ignored: {src_node}")
                continue
            dest_node.symlink_to(real_node.relative_to(src_node.parent, walk_up=True), real_node.is_dir())
        elif src_node.is_dir():
            dest_node.mkdir(exist_ok=True, mode=src_node.stat().st_mode)
        elif src_node.is_file():
            try:
                dest_node.hardlink_to(src_node)
            except UnsupportedOperation:
                src_node.copy(dest_node, preserve_metadata=True)
        else:
            log.debug(f"Unknown file type, ignored: {src_node}")
            continue
        log.debug(f"{src_node} -> {dest_node}")
