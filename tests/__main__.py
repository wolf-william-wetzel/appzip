"""Test the project with uv."""

import subprocess
import os
from contextlib import chdir

KWARGS = {
    "env": os.environ | {"DEBUG": "1"},  # Ensure debug for maximum output.
}
# Pack the test project and run the installer.
EXE = ["uv", "run"]
COMMANDS = [
[*EXE, "appzip", "testproject"],
[*EXE, "testproject/dist/testapp_1.2.3_installer.pyz"],
]


def main(commands: list[list[str] | str], kwargs: dict | None = None) -> int:
    """Run ``commands``, returning early if any fail."""
    for command in commands:
        if code := subprocess.run(command, **(kwargs if kwargs else {})).returncode:
            return code
    return 0


# uv run tests
if __name__ == "__main__":
    with chdir(os.path.dirname(__file__)):
        raise SystemExit(main(COMMANDS, KWARGS))
