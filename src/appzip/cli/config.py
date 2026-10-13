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
    exclude: tuple[str, ...] = ("build", "dist")


class Tool(Base):
    appzip: Appzip = field(default_factory=Appzip)


class ConfigFile(Base):
    """Represents the entire configuration file."""
    project: Project
    tool: Tool = field(default_factory=Tool)


class GenConfig:
    """Generated configuration values."""
    log_file: Path
    installer_path: Path
    dest_dir: Path


class Config(GenConfig):
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
        # Load values from config file.
        for name in get_annotations(self.__class__):
            self.set_attr_from_config(name, config.tool.appzip, config.project)
        # Calculate generated values.
        self.log_file = self.build_dir / "build.log"
        self.installer_path = self.dist_dir / f"{self.name}_{self.version}_installer.pyz"
        self.dest_dir = self.build_dir / self.installer_path.stem

    def set_attr_from_config(self, name: str, *tables: Struct):
        """Set attribute ``name`` from ``tables``, searching sequentially.

        Raise ``ValidationError`` if ``name`` isn't found.
        """
        for table in tables:
            if (value := getattr(table, name, None)) is not None:
                setattr(self, name, value)
                return
        raise ValidationError(f"Field '{name}' not found in config")

    def __rich_repr__(self):
        for name, value in vars(self).items():
            yield name, value


def load_config(path: Path) -> Config:
    """Load a config object from the given file."""
    BaseDirPath.base = path.parent  # Set the base dir to the config location.
    with open(path, encoding="utf-8") as file:
        return Config(toml.decode(file.read(), type=ConfigFile, dec_hook=dec_hook))
