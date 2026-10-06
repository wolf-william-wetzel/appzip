from pathlib import Path

from msgspec import Struct, field, toml


class BasePath(Path):
    """Type for the base directory, used for decoder hook and validation."""
    base_dir: Path  # The directory relative paths should be relative to.

    @classmethod
    def validate(cls, obj: str):
        path = Path(obj).expanduser()
        if not path.is_absolute():
            try:
                path = (cls.base_dir / path).resolve(True)
            except OSError:
                raise ValueError(f"'{path}' does not exist or contains symlink loops") from None
        if not path.is_dir():
            raise ValueError(f"'{path}' is not a directory")
        # Validating a new base dir changes it for all relative paths.
        cls.base_dir = path
        return cls(path)


class RelPath(Path):
    """Type for a path relative to base directory, used for decoder hook and validation."""
    @classmethod
    def validate(cls, obj: str):
        if Path(obj).is_absolute():
            raise ValueError("'{path}' is not relative")
        return cls(BasePath.base_dir / obj).resolve()


def factory[T](cls: type[T], *args, **kwargs):
    """Create a factory function for creating validator objects.

    ``*args`` and ``**kwargs`` are passed directly into the ``cls.validate`` method.
    """
    return lambda: cls.validate(*args, **kwargs)


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
    base_dir: BasePath = field(default_factory=factory(BasePath, "."))
    build_dir: RelPath = field(default_factory=factory(RelPath, "build"))
    dist_dir: RelPath = field(default_factory=factory(RelPath, "dist"))


class Tool(Base):
    appzip: Appzip = field(default_factory=Appzip)


class Config(Base):
    """Represents the entire configuration file."""
    project: Project = field(default_factory=Project)
    tool: Tool = field(default_factory=Tool)


def load_config(path: Path) -> Config:
    """Load a config object from the given file."""
    BasePath.base_dir = path.parent  # Set the base dir to the config location.
    with open(path) as file:
        return toml.decode(file.read(), type=Config, dec_hook=dec_hook)
