from typing import Set


class SenvError(Exception):
    pass


class SenvDuplicatedKeysInConfig(SenvError):
    def __init__(self, intersected_keys: Set[str]):
        self.intersected_keys = intersected_keys

    def __str__(self):
        return f"Keys {{{self.intersected_keys}}} are duplicated on senv and poetry"


class SenvInvalidPythonVersion(SenvError):
    pass


class SenvNotSupportedPlatform(SenvError):
    pass


class SenvBadConfiguration(SenvError):
    pass


class SenvNotAllPlatformsInBaseLockFile(SenvError):
    def __init__(self, platforms: Set[str]):
        self.missing_platforms = platforms

    def __str__(self):
        return (
            f"Missing platforms in base lock file: {', '.join(self.missing_platforms)}"
        )
