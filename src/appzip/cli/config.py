from pathlib import Path
from annotationlib import get_annotations

from msgspec import Struct, field, toml, ValidationError


def validate_dir(obj: str, create: bool = False) -> Path:
    """Perform directory validation.

    If the path exists and isn't a dir, an error is raised.
    If ``create`` is ``True`` and the path doesn't exist, it will be created.
    If ``create`` is ``False`` and the path doesn't exist, an error is raised.
    """
    path = Path(obj).expanduser()
    if not path.is_absolute():
        path = BaseDirPath.base / path
    try:
        if path.exists():
            if not path.is_dir():
                raise FileExistsError
        elif create:
            path.mkdir(parents=True, exist_ok=True)
        return path.resolve(True)
    except FileExistsError:
        raise ValueError(f"'{path}' is not a directory") from None
    except OSError:
        raise ValueError(f"'{path}' does not exist or contains symlink loops") from None


class BaseDirPath(Path):
    """Type for the base dir, used for decoder hook and validation."""
    base: Path  # Global access to the base directory.

    @classmethod
    def validate(cls, obj: str):
        # Validating a new base dir changes it for all relative paths.
        cls.base = (path := validate_dir(obj))
        return cls(path)


class DirPath(Path):
    """Type for a dir, used for decoder hook and validation."""
    @classmethod
    def validate(cls, obj: str):
        return cls(validate_dir(obj, create=True))


def dec_hook(type_: type, obj):
    if hasattr(type_, "validate") and callable(type_.validate):
        return type_.validate(obj)
    module = "" if type_.__module__ in (None, "builtins") else f"{type_.__module__}."
    raise NotImplementedError(f"unsupported type '{module}{type_.__qualname__}'")


class Base(Struct, frozen=True, rename="kebab"):
    """Base struct holding common settings."""
    pass


class Project(Base):
    name: str
    version: str | None = None
    description: str | None = None
    requires_python: str | None = None
    dependencies: list[str] = []


class Appzip(Base):
    version: str | None = None
    base_dir: BaseDirPath = field(default_factory=lambda: BaseDirPath.validate("."))
    build_dir: DirPath = field(default_factory=lambda: DirPath.validate("build"))
    dist_dir: DirPath = field(default_factory=lambda: DirPath.validate("dist"))
    include: tuple[str, ...] = ("**",)
    exclude: tuple[str, ...] = ()


class Tool(Base):
    appzip: Appzip = field(default_factory=Appzip)


class ConfigFile(Base):
    """Represents the entire configuration file."""
    project: Project
    tool: Tool = field(default_factory=Tool)


class Config:
    name: str
    version: str
    description: str | None
    requires_python: str | None
    dependencies: list[str]
    base_dir: Path
    build_dir: Path
    dist_dir: Path
    include: tuple[str, ...]
    exclude: tuple[str, ...]

    def __init__(self, config: ConfigFile):
        for name in get_annotations(self.__class__):
            if (value := getattr(config.tool.appzip, name, None)) is None:
                if (value := getattr(config.project, name, None)) is None:
                    raise ValidationError(f"Field '{name}' not found in config")
            setattr(self, name, value)

    def __rich_repr__(self):
        for name, value in vars(self).items():
            yield name, value


def load_config(path: Path) -> Config:
    """Load a config object from the given file."""
    BaseDirPath.base = path.parent  # Set the base dir to the config location.
    with open(path, encoding="utf-8") as file:
        return Config(toml.decode(file.read(), type=ConfigFile, dec_hook=dec_hook))
