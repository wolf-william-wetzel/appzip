from msgspec import Struct


class FrozenStruct(Struct, frozen=True):
    pass


class Config(FrozenStruct):
    """Represents the entire configuration file."""
    pass
