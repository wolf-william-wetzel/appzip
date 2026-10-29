import sys
from pathlib import Path
import os
from enum import StrEnum
import subprocess


class Platform(StrEnum):
    UNIX = "unix"
    LINUX = "unix"
    DARWIN = "unix"
    CYGWIN = "unix"
    FREEBSD = "unix"
    WINDOWS = "windows"
    WIN32 = "windows"
    FALLBACK = "fallback"
PLATFORM = getattr(Platform, sys.platform.upper(), Platform.FALLBACK)


type PlatformDirs = dict[Platform, list[str]]
INSTALL_DIRS: PlatformDirs = {
    Platform.UNIX: ["${XDG_DATA_HOME}", "~/.local/share"],
    Platform.WINDOWS: ["${APPDATA}", "~"],
    Platform.FALLBACK: ["~"],
}
bin_dir_list = ["${XDG_BIN_HOME}", "${XDG_DATA_HOME}/../bin", "~/.local/bin"]
BIN_DIRS: PlatformDirs = {
    Platform.UNIX: bin_dir_list,
    Platform.WINDOWS: bin_dir_list,
    Platform.FALLBACK: bin_dir_list,
}


def _get_dir(dirs: PlatformDirs) -> Path:
    for path in dirs[PLATFORM]:
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
    if PLATFORM is Platform.WINDOWS:
        # Compare case-insensitively.
        if str(path).lower() not in os.environ.get("PATH", "").lower():
            subprocess.run(f'setx PATH "%PATH%;{str(path)}"', shell=True)
    return path
