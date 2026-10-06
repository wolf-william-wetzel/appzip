from pathlib import Path
from types import SimpleNamespace

from msgspec import Struct, field, toml


# Load globals into namespace for pattern matching.
ns = SimpleNamespace(globals())

def dec_hook(type_: type, obj):
    match type_:
        case ns.Path:
            return Path(obj).expanduser().resolve()
        case _:
            module = "" if type_.__module__ in (None, "builtins") else f"{type_.__module__}."
            raise NotImplementedError(f"unsupported type '{module}{type_.__qualname__}'")


class Base(Struct, frozen=True, rename="kebab"):
    """Base struct holding common settings."""
    pass


class Project(Base):
    name: str | None = None
    version: str | None = None
    description: str | None = None
    requires_python: str | None = None
    dependencies: list[str] = []


class Appzip(Base):
    basedir: Path = field(default_factory=Path.cwd)


class Tool(Base):
    appzip: Appzip = field(default_factory=Appzip)


class Config(Base):
    """Represents the entire configuration file."""
    project: Project = field(default_factory=Project)
    tool: Tool = field(default_factory=Tool)


def load_config(text: str) -> Config:
    """Load a config object from the given text."""
    return toml.decode(text, type=Config, dec_hook=dec_hook)
