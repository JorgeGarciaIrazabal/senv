import os
import shutil
from enum import Enum
from pathlib import Path
from sys import platform
from typing import Any, Dict, List, Optional, Set

import toml
from conda_lock.conda_lock import DEFAULT_PLATFORMS
from ensureconda import ensureconda
from pydantic import BaseModel, Field, PrivateAttr, ValidationError, root_validator, validator

from senv.errors import SenvBadConfiguration, SenvNotSupportedPlatform
from senv.log import log


class BuildSystem(str, Enum):
    CONDA = "conda"
    POETRY = "poetry"


class _PoetrySenvShared(BaseModel):
    name: Optional[str] = Field(None)
    version: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    authors: Optional[List[str]] = Field(None)
    dependencies: Dict[str, Any] = Field(None)
    dev_dependencies: Dict[str, Any] = Field(None, alias="dev-dependencies")
    homepage: Optional[str] = Field(None)
    documentation: Optional[str] = Field(None)
    license: Optional[str] = Field(None)


class _SenvVEnv(BaseModel):
    build_system: Optional[BuildSystem] = Field(None, alias="build-system")
    conda_lock_platforms: Set[str] = Field(
        set(DEFAULT_PLATFORMS), alias="conda-lock-platforms"
    )
    conda_lock_dir: Path = Field(Path("."), alias="conda-lock-dir")
    name: Optional[str]


class _Senv(_PoetrySenvShared):
    conda_channels: Optional[List[str]] = Field([], alias="conda-channels")
    conda_publish_channel: str = Field(
        "default", alias="conda-publish-channel", env="SENV_CONDA_PUBLISH_CHANNEL"
    )
    poetry_publish_repository: Optional[str] = Field(
        None, alias="poetry-publish-repository", env="SENV_POETRY_PUBLISH_REPOSITORY"
    )
    conda_path: Optional[Path] = Field(None, alias="conda-path", env="SENV_CONDA_PATH")
    poetry_path: Optional[Path] = Field(
        None, alias="poetry-path", env="SENV_POETRY_PATH"
    )
    build_system: BuildSystem = Field(BuildSystem.CONDA, alias="build-system")
    venv: _SenvVEnv = Field(_SenvVEnv())
    conda_build_root: Path = Field(None, alias="conda-build-root")

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # if not build_system for the venv, then use the generic one
        if self.venv.build_system is None:
            self.venv.build_system = self.build_system

    @validator("conda_path", "poetry_path")
    def _validate_executable(cls, p: Path):
        if not p.exists():
            raise ValueError(f"Provided path {p} was not found")
        if not os.access(str(p), os.X_OK):
            raise ValueError(f"Provided path {p} is not executable")
        return p


class _Poetry(_PoetrySenvShared):
    pass


class _Tool(BaseModel):
    poetry: _Poetry = Field(_Poetry())
    senv: _Senv = Field(_Senv())


class Config(BaseModel):
    __instance: "Config"
    tool: _Tool
    _config_path: Path = PrivateAttr(None)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.package_name is None:
            raise ValueError("package name is required")
        if self.senv.conda_build_root is None:
            self.senv.conda_build_root = (
                    Path.home() / ".senv" / self.package_name / "dist_conda"
            )

    @classmethod
    def read_toml(cls, toml_path: Path) -> "Config":
        cls.__instance = Config._build_from_toml(toml_path)
        return cls.__instance

    @classmethod
    def _build_from_toml(cls, toml_path: Path) -> "Config":
        if not toml_path.exists():
            raise ValueError(f"{toml_path.absolute()} Not found")
        config_dict = toml.loads(toml_path.read_text())
        instance = Config(**config_dict)
        instance._config_path = toml_path.resolve().absolute()

        instance.validate_fields()
        return instance

    @classmethod
    def get(cls):
        return cls.__instance

    @property
    def config_path(self):
        return self._config_path

    @property
    def senv(self):
        return self.tool.senv

    @property
    def dependencies(self):
        return self.senv.dependencies or self.tool.poetry.dependencies

    @property
    def dev_dependencies(self):
        return self.senv.dev_dependencies or self.tool.poetry.dev_dependencies

    @property
    def version(self) -> str:
        return self.senv.version or self.tool.poetry.version

    @property
    def description(self) -> str:
        return self.senv.description or self.tool.poetry.description

    @property
    def documentation(self) -> str:
        return self.senv.documentation or self.tool.poetry.documentation

    @property
    def package_name(self) -> str:
        return self.senv.name or self.tool.poetry.name

    @property
    def homepage(self):
        return self.senv.homepage or self.tool.poetry.homepage or "__NONE__"

    @property
    def authors(self) -> List[str]:
        return self.senv.authors or self.tool.poetry.authors

    @property
    def license(self) -> str:
        return self.senv.license or self.tool.poetry.license or "Proprietary"

    @property
    def python_version(self) -> str:
        return self.dependencies.get("python", None)

    @property
    def venv_name(self) -> str:
        return self.senv.venv.name or self.package_name

    @property
    def conda_path(self) -> Path:
        return self.senv.conda_path or ensureconda(no_install=True, micromamba=False)

    @property
    def poetry_path(self) -> Path:
        return self.senv.poetry_path or shutil.which("poetry")

    @property
    def platform_conda_lock(self):
        if platform == "linux" or platform == "linux2":
            plat = "linux-64"
        elif platform == "darwin":
            plat = "osx-64"
        elif platform == "win32":
            plat = "win-64"
        else:
            raise SenvNotSupportedPlatform(f"Platform {platform} not supported")
        return self.senv.venv.conda_lock_dir / f"conda-{plat}.lock"

    def validate_fields(self):
        if self.poetry_path is None:
            log.warning(
                "No poetry executable found. "
                "Add poetry to your PATH or define it in the pyproject.toml"
                " with key 'tool.senv.poetry_path'"
            )
        if self.conda_path is None:
            log.warning(
                "No conda executable found. "
                "Add conda to your PATH or define it in the pyproject.toml"
                " with key 'tool.senv.conda_path'"
            )

        if self.senv.conda_build_root is None:
            raise SenvBadConfiguration("conda_build_root can not be None")

        try:
            self.senv.conda_build_root.resolve().relative_to(
                self.config_path.parent.resolve()
            )
            raise SenvBadConfiguration(
                "conda-build-root can not be a subdirectory of the project's directory"
            )
        except ValueError:
            pass

        # todo add more validations
