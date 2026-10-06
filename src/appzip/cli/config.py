from pathlib import Path

from msgspec import Struct, field, toml


def validate_dir(obj: str, strict: bool = False) -> Path:
    """Perform directory validation."""
    path = Path(obj).expanduser()
    if not path.is_absolute():
        path = BaseDirPath.base / path
    if path.exists() and not path.is_dir():
        raise ValueError(f"'{path}' is not a directory")
    try:
        return path.resolve(strict)
    except OSError:
        raise ValueError(f"'{path}' does not exist or contains symlink loops") from None


class BaseDirPath(Path):
    """Type for the base dir, used for decoder hook and validation."""
    base: Path  # Global access to the base directory.

    @classmethod
    def validate(cls, obj: str):
        # Validating a new base dir changes it for all relative paths.
        cls.base = (path := validate_dir(obj, True))
        return cls(path)


class DirPath(Path):
    """Type for a dir, used for decoder hook and validation."""
    @classmethod
    def validate(cls, obj: str):
        return cls(validate_dir(obj))


def dec_hook(type_: type, obj):
    if hasattr(type_, "validate") and callable(type_.validate):
        return type_.validate(obj)
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
    base_dir: BaseDirPath = field(default_factory=lambda: BaseDirPath.validate("."))
    build_dir: DirPath = field(default_factory=lambda: DirPath.validate("build"))
    dist_dir: DirPath = field(default_factory=lambda: DirPath.validate("dist"))
    include: tuple[str, ...] = ("./**",)
    exclude: tuple[str, ...] = ()


class Tool(Base):
    appzip: Appzip = field(default_factory=Appzip)


class Config(Base):
    """Represents the entire configuration file."""
    project: Project = field(default_factory=Project)
    tool: Tool = field(default_factory=Tool)


def load_config(path: Path) -> Config:
    """Load a config object from the given file."""
    BaseDirPath.base = path.parent  # Set the base dir to the config location.
    with open(path) as file:
        return toml.decode(file.read(), type=Config, dec_hook=dec_hook)
