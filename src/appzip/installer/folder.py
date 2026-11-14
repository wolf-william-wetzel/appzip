from pathlib import Path
import os
import subprocess
import logging

from .utils import Platform, getenv

log = logging.getLogger(__name__)

XDG_USER_DIRS_FILE = Path.home() / ".config/user-dirs.dirs"


def _get_dir(dirs: list[str], must_exist: bool = False) -> Path | None:
    for path in dirs:
        path = os.path.expanduser(os.path.expandvars(path))
        if path[0] in "$~":
            continue
        path = Path(path)
        if path.exists() and not path.is_dir():
            continue
        return path.resolve(strict=must_exist)
    return None


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
            if proc.returncode:
                log.debug(
                    f"%s\n\u2937 [error]%{"#X" if proc.returncode < 0 else "d"}",
                    proc.args, proc.returncode,
                )
    # Warn if path not in system path.
    if path_str not in sys_path:
        log.warning("%s is not in system path", path)


def _get_windows_folder(name: str) -> str | None:
    if not Platform.IS_WIN:
        return None

    try:
        import winreg
    except ImportError:
        # Get from subprocess.
        proc = subprocess.run(
            [
                "powershell",
                "-NoLogo",
                "-NonInteractive",
                "-NoProfile",
                "-C",
                f"[Environment]::GetFolderPath([Environment+SpecialFolder]::{name})",
            ],
            stdout=subprocess.PIPE,
            text=True,
        )
        return None if proc.returncode else proc.stdout
    try:
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            return str(winreg.QueryValueEx(key, name)[0])
    except OSError:
        return None


def _get_xdg_user_dir(name: str) -> str | None:
    if XDG_USER_DIRS_FILE.exists():
        with open(XDG_USER_DIRS_FILE) as file:
            for line in file:
                if name in line and "=" in line:
                    return line.rpartition("=")[2].strip().strip("\"'")
    return None


def get_install_dir() -> Path:
    paths = ["~"]
    if Platform.IS_UNIX:
        paths = ["${XDG_DATA_HOME}", "~/.local/share"]
    if Platform.IS_WIN:
        paths = ["${APPDATA}", "~"]
    return _get_dir(paths) or Path.cwd()


def get_desktop_dir() -> Path | None:
    path = _get_windows_folder("Desktop") or _get_xdg_user_dir("XDG_DESKTOP_DIR")
    paths = ["${XDG_DESKTOP_DIR}", "~/Desktop"]
    return _get_dir(paths if path is None else [path, *paths], must_exist=True)


def get_start_menu_dir() -> Path | None:
    if Platform.IS_WIN:
        path = _get_windows_folder("Programs")
        paths = ["${APPDATA}/Microsoft/Windows/Start Menu/Programs"] if path is None else [path]
    else:
        paths = ["~/Applications" if Platform.IS_MAC else "~/.local/share/applications"]
    return _get_dir(paths, must_exist=True)


def get_bin_dir() -> Path | None:
    path = _get_dir(["${XDG_BIN_HOME}", "${XDG_DATA_HOME}/../bin", "~/.local/bin"])
    if path is not None:
        path.mkdir(parents=True, exist_ok=True)
        _ensure_on_path(path)
    return path
