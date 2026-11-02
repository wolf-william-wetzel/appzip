"""Test the project with uv."""

import subprocess
import os
from contextlib import chdir
import sys

NEW_ENV: dict[str, str] = {
    "DEBUG": "1",  # Ensure debug for maximum output.
    "TTY_INTERACTIVE": "0",  # No user input.
}
QUIET_ENV: dict[str, str] = {
    "TTY_INTERACTIVE": "0",  # No user input.
}
KWARGS = {
    "env": os.environ | NEW_ENV,
}
QUIET_KWARGS = {
    "env": os.environ | QUIET_ENV,
}
# The commands to be run.
EXE = ["uv", "run"]
INSTALLER_PATH = "testproject/dist/testapp_1.2.3_installer.pyz"
PACK_HELP_COMMAND = [*EXE, "appzip", "-h"]
PACK_COMMAND = [*EXE, "appzip", "testproject"]
INSTALLER_HELP_COMMAND = [*EXE, INSTALLER_PATH, "-h"]
INSTALL_COMMAND = [*EXE, INSTALLER_PATH, "-r"]
COMMANDS = {
    "help": [PACK_HELP_COMMAND, INSTALLER_HELP_COMMAND],
    "pack": [PACK_COMMAND, INSTALLER_HELP_COMMAND],
    "install": [PACK_COMMAND, INSTALL_COMMAND],
    "reinstall": [INSTALL_COMMAND],
}
DEFAULT = "pack"


def run_commands(commands: list[list[str] | str], kwargs: dict | None = None) -> int:
    """Run ``commands``, returning early if any fail."""
    for command in commands:
        if code := subprocess.run(command, **(kwargs if kwargs else {})).returncode:
            return code
    return 0


def main():
    if (cmds := COMMANDS.get(DEFAULT if len(sys.argv) < 2 else sys.argv[1])) is None:
        raise SystemExit(
            f"Usage: python3 {sys.argv[0]} [{"|".join(COMMANDS.keys())}] (default: {DEFAULT}) [-q/--quiet]"
        )
    with chdir(os.path.dirname(__file__)):
        raise SystemExit(run_commands(cmds, QUIET_KWARGS if sys.argv[-1] in ("-q", "--quiet") else KWARGS))


# uv run tests [test]
if __name__ == "__main__":
    main()
