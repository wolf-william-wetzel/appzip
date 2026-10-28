import sys
from pathlib import Path
import os
from enum import StrEnum


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
    Platform.WINDOWS: ["${APPDATA}"],
    Platform.FALLBACK: [],
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
