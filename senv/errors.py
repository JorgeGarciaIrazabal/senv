from pathlib import Path
from typing import List


class SenvError(Exception):
    pass


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
