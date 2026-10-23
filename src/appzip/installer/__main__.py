from .metadata import Metadata


def main():
    print("Running installer...")
    metadata = Metadata()
    print(metadata.name)
    print(metadata.version)
    print(metadata.description)
