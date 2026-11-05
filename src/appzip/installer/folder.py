from pathlib import Path
import os
import subprocess

from .utils import Platform

INSTALL_DIRS = ["~"]
if Platform.IS_UNIX:
    INSTALL_DIRS = ["${XDG_DATA_HOME}", "~/.local/share"]
if Platform.IS_WIN:
    INSTALL_DIRS = ["${APPDATA}", "~"]

BIN_DIRS = ["${XDG_BIN_HOME}", "${XDG_DATA_HOME}/../bin", "~/.local/bin"]


def _get_dir(dirs: list[str]) -> Path:
    for path in dirs:
        try:
            path = os.path.expanduser(os.path.expandvars(path))
            assert path[0] not in "$~"
        except RuntimeError, AssertionError:
            continue
        return Path(path)
    return Path.cwd()


def get_install_dir() -> Path:
    return _get_dir(INSTALL_DIRS)


def get_bin_dir() -> Path:
    path = _get_dir(BIN_DIRS)
    # Create and resolve the path.
    try:
        path.mkdir(parents=True, exist_ok=True)
        path = path.resolve(strict=True)
    # Upon failure, default to cwd.
    except OSError:
        return Path.cwd()
    # Add to path on Windows if needed.
    if Platform.IS_WIN:
        # Compare case-insensitively.
        if str(path).lower() not in os.environ.get("PATH", "").lower():
            subprocess.run(f'setx PATH "%PATH%;{str(path)}"', shell=True)
    return path
