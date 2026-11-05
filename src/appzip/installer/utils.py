import os
import sys
import logging
from pathlib import Path, UnsupportedOperation
import subprocess
from zipfile import ZipFile
import stat

__all__ = [
    "Platform",
    "getenv",
    "LOG_LEVEL",
    "LOG_LEVELS",
    "is_term",
    "can_interact",
    "can_colorize",
    "extract_subdir",
    "get_venv_py",
    "venv_install",
]

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


LOG_LEVELS = logging.getLevelNamesMapping()
LOG_LEVELS.pop("CRITICAL")
LOG_LEVELS.pop("WARNING")
LOG_LEVELS.pop("NOTSET")

LOG_LEVEL = (getenv("LOGLEVEL") or getenv("LOG_LEVEL")).upper()
LOG_LEVEL = {"CRITICAL": "FATAL", "WARNING": "WARN"}.get(LOG_LEVEL, LOG_LEVEL)
if LOG_LEVEL not in LOG_LEVELS:
    LOG_LEVEL = "DEBUG" if getenv("DEBUG") else "WARN"


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


def get_venv_py(venv_dir: Path, windowed: bool = False) -> Path:
    """Get the path to the python executable for ``venv_dir``."""
    py_name = f"python{"w" if windowed else ""}.exe" if Platform.IS_WIN else "python"
    path = venv_dir / ("Scripts" if Platform.IS_WIN else "bin") / py_name
    if path.exists():
        return path
    raise FileNotFoundError(f"no {py_name} found in {venv_dir}")


def venv_install(venv_dir: Path, dependencies: list[str], show_output: bool = False):
    """Install ``dependencies`` into ``venv_dir``."""
    args = [str(get_venv_py(venv_dir)), "-m", "pip", "install", *dependencies]
    log.debug("[l_yellow]{0} [d][fg]{1} [nd]{2} {3} [green]{4}[/]".format(*args[:4], " ".join(args[4:])))
    subprocess.check_call(args, stdout=None if show_output else subprocess.DEVNULL, stderr=subprocess.STDOUT)
