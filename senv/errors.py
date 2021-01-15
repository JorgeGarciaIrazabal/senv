from pathlib import Path
from typing import List, Set


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


class SenvNotAllRequiredLockFiles(SenvError):
    def __init__(self, missing_lock_files: List[Path]):
        self.missing_lock_files = missing_lock_files

    def __str__(self):
        files = "\n-".join([str(f.resolve()) for f in self.missing_lock_files])
        return f"Missing files: \n-{files}"
