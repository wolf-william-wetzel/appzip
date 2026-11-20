import os
import sys
import logging
from pathlib import Path, UnsupportedOperation
from zipfile import ZipFile
import stat
import shutil
from functools import cache
import subprocess
import shlex

__all__ = [
    "InstallerExit",
    "Platform",
    "getenv",
    "UV_EXE",
    "LOG_LEVEL",
    "LOG_LEVELS",
    "get_ep_script_name",
    "run_pwsh_cmd",
    "run_pwsh_file",
    "rmtree",
    "is_term",
    "can_interact",
    "can_colorize",
    "extract_subdir",
    "write_ep_script",
    "write_executable_file",
    "write_console_script",
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

EP_SCRIPT_MARKER = "-s"
EP_SCRIPT = """\
#!{interpreter}
import subprocess, os, sys
if len(sys.argv) < 3:
    raise SystemExit("need at least 2 args, only %%d provided" %% (len(sys.argv) - 1))
args = [{interpreter!r}]
if sys.argv[2] == "%s":
    args.append(sys.argv[1])
else:
    args += ["-c", "import %%s;%%s.%%s()" %% (sys.argv[1], sys.argv[1], sys.argv[2])]
proc = subprocess.run(args + sys.argv[3:], cwd={cwd!r}, env=os.environ | dict(PYTHONSAFEPATH=""))
sys.exit(proc.returncode)
""" % EP_SCRIPT_MARKER
EP_SCRIPT_NAME = "ep.py"
EP_SCRIPT_NAME_W = "ep.pyw"
EXTRA_ARGS_MARKER = "%*" if Platform.IS_WIN else '"$@"'


def get_ep_script_name(windowed: bool = False):
    return EP_SCRIPT_NAME_W if Platform.IS_WIN and windowed else EP_SCRIPT_NAME


def run_pwsh_cmd(command: str) -> subprocess.CompletedProcess[str]:
    return _run_pwsh_process(["-Command", command])


def run_pwsh_file(path: Path) -> subprocess.CompletedProcess[str]:
    return _run_pwsh_process(["-File", str(path)])


def _run_pwsh_process(args: list[str]) -> subprocess.CompletedProcess[str]:
    if not Platform.IS_WIN:
        raise NotImplementedError(f"PowerShell only available on Windows, not {Platform.NAME}")
    return subprocess.run([
        "powershell.exe",
        "-NoLogo",
        "-NonInteractive",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        *args,
    ], capture_output=True, text=True)


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

    if sys.platform == "win32":
        try:
            import nt
            if not nt._supports_virtual_terminal():  # noqa
                return False
        except (ImportError, AttributeError):
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


def write_ep_script(venv_dir: Path | None, app_dir: Path, cwd_name: str):
    _write_ep_script(venv_dir, app_dir, cwd_name)
    if Platform.IS_WIN:
        _write_ep_script(venv_dir, app_dir, cwd_name, True)


def _write_ep_script(venv_dir: Path | None, app_dir: Path, cwd_name: str, windowed: bool = False):
    text = EP_SCRIPT.format(interpreter=get_python(venv_dir, windowed), cwd=str(app_dir / cwd_name))
    write_executable_file(app_dir / (EP_SCRIPT_NAME_W if windowed else EP_SCRIPT_NAME), text)


def write_executable_file(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` and make it executable."""
    with open(path, "w") as f:
        f.write(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def quote_args(args: list[str | Path]) -> str:
    if not Platform.IS_WIN:
        return shlex.join(str(a) for a in args)
    win_args = []
    for i, arg in enumerate(args):
        if i == 0 or isinstance(arg, Path):
            arg = f'"{arg}"'
        win_args.append(arg)
    return " ".join(win_args)


def write_console_script(path: Path, ep_script: Path, module: str, attr: str):
    args: list[str | Path] = [
        get_python(),
        ep_script,
        module,
        attr or EP_SCRIPT_MARKER,
        EXTRA_ARGS_MARKER,
    ]
    text = quote_args(args)
    log.debug(f"Console script: [i]{text}")
    write_executable_file(path, text)


@cache
def get_python(venv_dir: Path | None = None, windowed: bool = False) -> str:
    """Return path to python executable as a string. Return system python if ``venv_dir`` is None."""
    return _get_sys_py(windowed) if venv_dir is None else _get_venv_py(venv_dir, windowed)


def _get_sys_py(windowed: bool = False) -> str:
    if not sys.executable:
        raise FileNotFoundError("Path to python binary not found.")
    if windowed and Platform.IS_WIN:
        path = Path(sys.executable).parent / "pythonw.exe"
        if path.exists():
            return str(path)
    return sys.executable


def _get_venv_py(venv_dir: Path, windowed: bool = False) -> str:
    """Get the path to the python executable for ``venv_dir``."""
    py_name = f"python{"w" if windowed else ""}.exe" if Platform.IS_WIN else "python"
    path = venv_dir / ("Scripts" if Platform.IS_WIN else "bin") / py_name
    if path.exists():
        return str(path)
    raise FileNotFoundError(f"[error]no {py_name} found in {venv_dir}")
