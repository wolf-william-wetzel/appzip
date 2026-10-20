from pathlib import Path
from annotationlib import get_annotations
from platform import python_version
from importlib.metadata import EntryPoint, EntryPoints  # noqa

from msgspec import Struct, field, toml, ValidationError
from packaging.specifiers import SpecifierSet
from packaging.requirements import Requirement
from packaging.dependency_groups import DependencyGroupResolver


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
    if type_ is EntryPoints:
        eps = []
        for group, ep in obj.items():
            if not group.startswith("appzip."):
                continue
            for name, value in ep.items():
                eps.append(EntryPoint(name, value, group))
        return EntryPoints(eps)
    if type_ in (Requirement, SpecifierSet, DependencyGroupResolver):
        return type_(obj)
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
    description: str = ""
    requires_python: SpecifierSet = SpecifierSet(f">={python_version()}")
    dependencies: list[Requirement] = []
    entry_points: EntryPoints = EntryPoints()


class Appzip(Base):
    version: str | None = None
    base_dir: BaseDirPath = field(default_factory=lambda: BaseDirPath.validate("."))
    build_dir: DirPath = field(default_factory=lambda: DirPath.validate("build"))
    dist_dir: DirPath = field(default_factory=lambda: DirPath.validate("dist"))
    include: tuple[str, ...] = ("**/*",)
    exclude: tuple[str, ...] = ("build", "dist")


class Tool(Base):
    appzip: Appzip = field(default_factory=Appzip)


class ConfigFile(Base):
    """Represents the entire configuration file."""
    project: Project
    dependency_groups: DependencyGroupResolver = DependencyGroupResolver({})
    tool: Tool = field(default_factory=Tool)


class GenConfig:
    """Generated configuration values."""
    log_file: Path  # Filename of log file inside build_dir.
    installer_path: Path  # Filename of final installer file inside dist_dir.
    dest_dir: Path  # Subfolder of build_dir where files are copied.
    app_dir: Path  # Subfolder of dest_dir where app is stored.
    metadata_file: Path  # Filename of metadata file inside dest_dir.
    entry_point: Path  # Filename of installer entry point inside dest_dir.
    minimum_python: int  # Minimum python hex version for the app.


class Config(GenConfig):
    name: str
    version: str
    description: str
    requires_python: SpecifierSet
    dependencies: list[Requirement]
    entry_points : EntryPoints
    base_dir: Path
    build_dir: Path
    dist_dir: Path
    include: tuple[str, ...]
    exclude: tuple[str, ...]

    def __init__(self, config: ConfigFile):
        # Load values from config file.
        for name in get_annotations(self.__class__):
            self.set_attr_from_config(name, config.tool.appzip, config.project)
        # Add appzip dependencies.
        try:
            self.dependencies.extend(config.dependency_groups.resolve("appzip"))
        except* LookupError:
            pass
        # Calculate generated values.
        self.log_file = self.build_dir / "build.log"
        self.installer_path = self.dist_dir / f"{self.name}_{self.version}_installer.pyz"
        self.dest_dir = self.build_dir / self.installer_path.stem
        self.app_dir = self.dest_dir / "app"
        self.metadata_file = self.dest_dir / "metadata.json"
        self.entry_point = self.dest_dir / "__main__.py"
        if not (minor := next(self.requires_python.filter(range(14, 255), key=lambda i: f"3.{i}"), 0)):
            raise ValidationError(f"Minimum python version couldn't be determined from '{self.requires_python!s}'")
        self.minimum_python = int(f"3{minor:0>2x}00f0", 16)

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
