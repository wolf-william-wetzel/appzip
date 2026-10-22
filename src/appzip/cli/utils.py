from pathlib import Path

HOME = Path.home()
CWD = Path.cwd()  # Shouldn't change throughout program run.


class Format:
    """Class to hold utility functions relating to formatting paths and links."""
    glyphs = {
        CWD: ".",
        CWD.parent: "..",
        HOME: "~",
    }
    DEFAULT_GLYPH = "..."

    @classmethod
    def path(cls, path: Path, *args: Path) -> str:
        """Format ``path`` as posix, shortening it if possible.

        If ``path`` is a directory, append a trailing slash.
        Check for shortening in the following order: ``.``, ``..``, ``~``.
        Extra args will be searched before the defaults, with a replacement string of ``...``.
        """
        dir_str = "/" if path.is_dir() else ""
        for parent in args + tuple(cls.glyphs.keys()):
            if path.is_relative_to(parent):
                return f"{cls.glyphs.get(parent, cls.DEFAULT_GLYPH)}/{path.relative_to(parent).as_posix()}{dir_str}"
        return f"{'' if path.is_absolute() else f'{cls.DEFAULT_GLYPH}/'}{path.as_posix()}{dir_str}"

    @classmethod
    def node(cls, node: Path, base: Path, real: Path | None = None) -> str:
        """Format ``node`` with an optional real path for symlinks. Both will be checked against ``base``."""
        return f"{cls.path(node, base)}{f' -> {cls.path(real, base)}' if real else ''}"

    @classmethod
    def link(cls, path: str | Path, text: str = "") -> str:
        """Return rich markup linking ``text`` to ``path``.

        If ``text`` is the empty string, it becomes formatted ``path``.
        """
        return f"[link={path}]{text if text else cls.path(Path(path))}[/]"
