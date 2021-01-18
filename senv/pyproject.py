import os
import shutil
from copy import deepcopy
from enum import Enum
from pathlib import Path
from sys import platform
from typing import Any, Dict, List, Optional, Set

import toml
from conda_lock.conda_lock import DEFAULT_PLATFORMS
from ensureconda import ensureconda
from pydantic import BaseModel, Field, PrivateAttr, root_validator, validator

from senv.errors import SenvBadConfiguration, SenvNotSupportedPlatform
from senv.log import log


class BuildSystem(str, Enum):
    CONDA = "conda"
    POETRY = "poetry"


class _SenvVEnv(BaseModel):
    build_system: Optional[BuildSystem] = Field(None, alias="build-system")
    conda_lock_platforms: Set[str] = Field(
        set(DEFAULT_PLATFORMS), alias="conda-lock-platforms"
    )
    venv_lock_dir: Path = Field(Path("venv_locks_dir"), alias="venv-lock-dir")
    name: Optional[str]

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
        return self.venv_lock_dir / f"conda-{plat}.lock"


class _Senv(BaseModel):
    venv: _SenvVEnv = Field(_SenvVEnv())
    # poetry shared
    name: Optional[str] = Field(None)
    version: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    authors: Optional[List[str]] = Field(None)
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    dev_dependencies: Dict[str, Any] = Field(
        default_factory=dict, alias="dev-dependencies"
    )
    scripts: Dict[str, str] = Field(default_factory=dict)
    homepage: Optional[str] = Field(None)
    documentation: Optional[str] = Field(None)
    license: str = Field("Proprietary")

    # senv specific
    # todo move some of this to a _Package model
    conda_path: Optional[Path] = Field(None, alias="conda-path", env="SENV_CONDA_PATH")
    conda_build_path: Path = Field(
        None, alias="conda-build-path", env="SENV_CONDA_BUILD_PATH"
    )
    conda_channels: Optional[List[str]] = Field([], alias="conda-channels")
    conda_publish_channel: Optional[str] = Field(
        None, alias="conda-publish-channel", env="SENV_CONDA_PUBLISH_CHANNEL"
    )
    package_lock_dir: Path = Field(Path("package_locks_dir"), alias="package-lock-dir")
    poetry_publish_repository: Optional[str] = Field(
        None, alias="poetry-publish-repository", env="SENV_POETRY_PUBLISH_REPOSITORY"
    )
    poetry_path: Optional[Path] = Field(
        None, alias="poetry-path", env="SENV_POETRY_PATH"
    )
    build_system: BuildSystem = Field(BuildSystem.CONDA, alias="build-system")

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


class _Tool(BaseModel):
    senv: _Senv = ...


class PyProject(BaseModel):
    __instance: "PyProject"
    tool: _Tool
    _config_path: Path = PrivateAttr(None)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.package_name is None:
            raise ValueError("package name is required")
        if self.senv.conda_build_path is None:
            self.senv.conda_build_path = (
                Path.home() / ".senv" / self.package_name / "dist_conda"
            )

    @root_validator(pre=True)
    def combine_senv_and_poetry(cls, values: Dict[str, Any]):
        values_copy = deepcopy(values)
        tool = values_copy.get("tool", {})
        poetry = tool.get("poetry", {})
        senv = tool.get("senv", {})
        poetry.update(senv)
        tool["senv"] = poetry
        tool.pop("poetry", None)
        return values_copy

    @root_validator
    def venv_name_defaults_to_package_name(cls, values: Dict[str, Any]):
        if len(values) == 0:
            # it is likely that another validation failed before this one
            return values
        tool: _Tool = values.get("tool")
        tool.senv.venv.name = tool.senv.venv.name or tool.senv.name
        return values

    @classmethod
    def read_toml(cls, toml_path: Path) -> "PyProject":
        cls.__instance = PyProject._build_from_toml(toml_path)
        return cls.__instance

    @classmethod
    def _build_from_toml(cls, toml_path: Path) -> "PyProject":
        if not toml_path.exists():
            raise ValueError(f"{toml_path.absolute()} Not found")
        config_dict = toml.loads(toml_path.read_text())
        instance = PyProject(**config_dict)
        instance._config_path = toml_path.resolve().absolute()

        instance.validate_fields()
        return instance

    @classmethod
    def get(cls) -> "PyProject":
        return cls.__instance

    @property
    def config_path(self):
        return self._config_path

    @property
    def senv(self) -> _Senv:
        return self.tool.senv

    @property
    def venv(self) -> _SenvVEnv:
        return self.tool.senv.venv

    @property
    def version(self) -> str:
        return self.senv.version

    @property
    def package_name(self) -> str:
        return self.senv.name

    @property
    def python_version(self) -> str:
        return self.senv.dependencies.get("python", None)

    @property
    def conda_path(self) -> Path:
        return self.senv.conda_path or ensureconda(
            no_install=True, micromamba=False, mamba=False
        )

    @property
    def poetry_path(self) -> Path:
        return self.senv.poetry_path or shutil.which("poetry")

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

        if self.senv.conda_build_path is None:
            raise SenvBadConfiguration("conda_build_root can not be None")

        try:
            self.senv.conda_build_path.resolve().relative_to(
                self.config_path.parent.resolve()
            )
            raise SenvBadConfiguration(
                "conda-build-path can not be a subdirectory of the project's directory"
            )
        except ValueError:
            pass

        # todo add more validations
