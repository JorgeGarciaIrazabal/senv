from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import appdirs
from pydantic import BaseModel, BaseSettings, Field


class LockFileMetaData(BaseModel):
    package_name: Optional[str] = None
    entry_points: List[str] = Field(default_factory=list)
    version: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CombinedCondaLock(BaseModel):
    metadata: LockFileMetaData
    platform_tar_links: Dict[str, List[str]] = Field(default_factory=dict)


class Settings(BaseSettings):
    INSTALLATION_PATH: Path = Field(Path(appdirs.user_data_dir("senvx")))
    BIN_DIR: Path = Field(Path.home() / ".local" / "bin")

    class Config:
        env_prefix = "SENVX_"
