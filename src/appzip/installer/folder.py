from pathlib import Path
import os
import subprocess
import logging

from .utils import Platform, getenv

log = logging.getLogger(__name__)

INSTALL_DIRS = ["~"]
if Platform.IS_UNIX:
    INSTALL_DIRS = ["${XDG_DATA_HOME}", "~/.local/share"]
if Platform.IS_WIN:
    INSTALL_DIRS = ["${APPDATA}", "~"]

BIN_DIRS = ["${XDG_BIN_HOME}", "${XDG_DATA_HOME}/../bin", "~/.local/bin"]


def _get_dir(dirs: list[str]) -> Path:
    for path in dirs:
        path = os.path.expanduser(os.path.expandvars(path))
        if path[0] in "$~":
            continue
        path = Path(path)
        if path.exists() and not path.is_dir():
            continue
        return path.resolve()
    return Path.cwd()


def _ensure_on_path(path: Path):
    path_str = str(path)
    sys_path = getenv("PATH")
    # Windows-only.
    if Platform.IS_WIN:
        # Compare case-insensitively.
        path_str, sys_path = path_str.lower(), sys_path.lower()
        # Add to system path if needed.
        if path_str not in sys_path:
            proc = subprocess.run(f'setx PATH "%PATH%;{path}"', shell=True)
            log.debug(proc)
    # Warn if path not in system path.
    if path_str not in sys_path:
        log.warning("%s is not in system path", path)


def get_install_dir() -> Path:
    return _get_dir(INSTALL_DIRS)


def get_bin_dir() -> Path:
    path = _get_dir(BIN_DIRS)
    path.mkdir(parents=True, exist_ok=True)
    _ensure_on_path(path)
    return path
