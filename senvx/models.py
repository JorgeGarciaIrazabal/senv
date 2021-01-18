from datetime import datetime
from pathlib import Path
from typing import List

import appdirs
from pydantic import BaseModel, BaseSettings, Field


class SenvxError(Exception):
    pass


class SenvxMalformedAppLockFile(SenvxError):
    pass


class LockFileMetaData(BaseModel):
    package_name: str
    entry_points: List[str] = Field(default_factory=list)
    create_at: datetime = Field(default_factory=datetime.utcnow)

    @staticmethod
    def from_lock_path(lockfile: Path) -> "LockFileMetaData":
        lock_content = lockfile.read_text()
        if "@METADATA_INIT" not in lock_content or "@METADATA_END" not in lock_content:
            raise SenvxMalformedAppLockFile("No @METADATA keys required")

        commented_metadata = lock_content.split("@METADATA_INIT", 1)[1].rsplit(
            "@METADATA_END"
        )[0]
        metadata_json = "\n".join(
            [l.lstrip("#").strip() for l in commented_metadata.splitlines()]
        ).strip()
        return LockFileMetaData.parse_raw(metadata_json)


class Settings(BaseSettings):
    INSTALLATION_PATH: Path = Field(Path(appdirs.user_data_dir("senvx")))
    BIN_DIR: Path = Field(Path.home() / ".local" / "bin")

    class Config:
        env_prefix = "SENVX_"
