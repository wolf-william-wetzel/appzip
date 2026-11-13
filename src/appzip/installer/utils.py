import os
import sys
import logging
from pathlib import Path, UnsupportedOperation
from zipfile import ZipFile
import stat
import shutil
from functools import cache

__all__ = [
    "InstallerExit",
    "Platform",
    "getenv",
    "UV_EXE",
    "LOG_LEVEL",
    "LOG_LEVELS",
    "is_term",
    "rmtree",
    "can_interact",
    "can_colorize",
    "extract_subdir",
    "make_ep_file",
    "get_python",
]


class InstallerExit(Exception):
    """Exit installer with exit code 0."""


log = logging.getLogger(__name__)


class Platform:
    NAME = sys.platform
    UNIX_PLATFORMS = [
        "linux",
        "cygwin",
        "freebsd",
        "darwin",
    ]
    IS_UNIX = NAME in UNIX_PLATFORMS
    IS_MAC = NAME == "darwin"
    IS_WIN = NAME == "win32"


def getenv(var: str, fallback: str = "") -> str:
    try:
        return os.environ.get(var, fallback)
    except Exception:  # noqa
        return fallback


UV_EXE = shutil.which("uv")

LOG_LEVELS = logging.getLevelNamesMapping()
LOG_LEVELS.pop("CRITICAL")
LOG_LEVELS.pop("WARNING")
LOG_LEVELS.pop("NOTSET")

LOG_LEVEL = (getenv("LOGLEVEL") or getenv("LOG_LEVEL")).upper()
LOG_LEVEL = {"CRITICAL": "FATAL", "WARNING": "WARN"}.get(LOG_LEVEL, LOG_LEVEL)
if LOG_LEVEL not in LOG_LEVELS:
    LOG_LEVEL = "DEBUG" if getenv("DEBUG") else "WARN"


def rmtree(path: Path):
    errors: list[tuple[str, BaseException]] = []
    shutil.rmtree(path, onexc=lambda _, p, e: errors.append((p, e)))
    if errors:
        raise OSError("Couldn't remove the following file(s):\n" + "\n".join(f"{p} -> {e}" for p, e in errors))


def is_term(file=None) -> bool:
    """Modified from the Python 3.15 stdlib."""
    if file is None:
        file = sys.stdout

    if getenv("TTY_COMPATIBLE") == "1":
        return True
    if getenv("TTY_COMPATIBLE") == "0":
        return False

    if getenv("TERM") in ("dumb", "unknown"):
        return False

    if not hasattr(file, "fileno"):
        return False

    try:
        return os.isatty(file.fileno())
    except OSError:
        try:
            return hasattr(file, "isatty") and file.isatty()
        except ValueError:
            return False


def can_interact(file=None) -> bool:
    if getenv("TTY_INTERACTIVE") == "1":
        return True
    if getenv("TTY_INTERACTIVE") == "0":
        return False
    return is_term(file)


def can_colorize(file=None) -> bool:
    """Modified from the Python 3.15 stdlib."""
    if not sys.flags.ignore_environment:
        if getenv("PYTHON_COLORS") == "0":
            return False
        if getenv("PYTHON_COLORS") == "1":
            return True
    if getenv("NO_COLOR"):
        return False
    if getenv("FORCE_COLOR"):
        return True

    if sys.platform == "win32":
        try:
            import nt
            if not nt._supports_virtual_terminal():  # noqa
                return False
        except (ImportError, AttributeError):
            return False

    return is_term(file)


def extract_subdir(zf: ZipFile, subdir: str, dest: Path) -> None:
    """Extract all members of ``subdir`` from ``zf`` to ``dest``, preserving symlinks."""
    for info in (i for i in zf.infolist() if i.filename.startswith(subdir)):
        log.debug(f"Extracting %s", info)

        # Extract non-symlinks normally.
        if not stat.S_ISLNK(info.external_attr >> 16):
            zf.extract(info, dest)
            continue

        # Get the symlink's extracted location.
        path = dest / info.filename
        # Target is stored as posix with trailing '/' for directories.
        # Target is relative to parent of symlink.
        target = zf.read(info).decode("utf-8")
        try:
            # Extract the symlink.
            path.symlink_to(target, target.endswith("/"))
        except UnsupportedOperation:
            msg = "\nSymlink creation not available on this platform."
            log.exception(f"Cannot create symlink: %s -> %s{msg}", path, target)
        except OSError:
            win = ""
            if Platform.IS_WIN:
                win = "\nTry running as administrator or activating Windows Developer Mode."
            log.exception(f"Cannot create symlink: %s -> %s{win}", path, target)


def make_ep_file(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` and make it executable."""
    with open(path, "w") as f:
        f.write(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@cache
def get_python(venv_dir: Path | None = None, windowed: bool = False) -> str:
    """Return path to python executable as a string. Return system python if ``venv_dir`` is None."""
    return get_sys_py(windowed) if venv_dir is None else get_venv_py(venv_dir, windowed)


def get_sys_py(windowed: bool = False) -> str:
    if not sys.executable:
        raise FileNotFoundError("Path to python binary not found.")
    if windowed and Platform.IS_WIN:
        path = Path(sys.executable).parent / "pythonw.exe"
        if path.exists():
            return str(path)
    return sys.executable


def get_venv_py(venv_dir: Path, windowed: bool = False) -> str:
    """Get the path to the python executable for ``venv_dir``."""
    py_name = f"python{"w" if windowed else ""}.exe" if Platform.IS_WIN else "python"
    path = venv_dir / ("Scripts" if Platform.IS_WIN else "bin") / py_name
    if path.exists():
        return str(path)
    raise FileNotFoundError(f"[error]no {py_name} found in {venv_dir}")
