import shutil
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import toml
from conda_lock.conda_lock import DEFAULT_PLATFORMS
from ensureconda import ensureconda
from pydantic import BaseModel, Field, validator, PrivateAttr

from pysenv.log import log


class BuildSystem(str, Enum):
    CONDA = "conda"
    POETRY = "poetry"


class _PoetryPysenvShared(BaseModel):
    name: Optional[str] = Field(None)
    version: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    authors: Optional[List[str]] = Field(None)
    dependencies: Dict[str, Any] = Field(None)
    dev_dependencies: Dict[str, Any] = Field(None, alias="dev-dependencies")
    homepage: Optional[str] = Field(None)


class _PysenvVEnv(BaseModel):
    build_system: BuildSystem = Field(BuildSystem.CONDA, alias="build-system")
    conda_platforms: Set[str] = Field(set(DEFAULT_PLATFORMS), alias="conda-platforms")
    name: Optional[str]


class _Pysenv(_PoetryPysenvShared):
    name: Optional[str] = Field(None)
    version: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    authors: Optional[str] = Field(None)
    conda_channels: Optional[List[str]] = Field([], alias="conda-channels")
    conda_path: Optional[Path] = Field(None, alias="conda-path")
    poetry_path: Optional[Path] = Field(None, alias="poetry-path")
    venv: _PysenvVEnv = Field(_PysenvVEnv())

    @validator("conda_path", "poetry_path")
    def _validate_executable(cls, p: Path):
        if not p.exists():
            raise ValueError(f"Provided path {p} not found")
        if not os.access(str(p), os.X_OK):
            raise ValueError(f"Provided path {p} not executable")
        return p


class _Poetry(_PoetryPysenvShared):
    pass


class _Tool(BaseModel):
    poetry: _Poetry = Field(_Poetry())
    pysenv: _Pysenv = Field(_Pysenv())


class Config(BaseModel):
    __instance: "Config"
    tool: _Tool
    _config_path: Path = PrivateAttr(None)

    @classmethod
    def read_toml(cls, toml_path: Path):
        config_dict = toml.loads(toml_path.read_text())
        cls.__instance = Config(**config_dict)
        cls.__instance._config_path = toml_path.resolve().absolute()
        cls.__instance.validate_fields()

    @classmethod
    def get(cls):
        return cls.__instance

    @property
    def config_path(self):
        return self._config_path

    @property
    def pysenv(self):
        return self.tool.pysenv

    @property
    def dependencies(self):
        return self.pysenv.dependencies or self.tool.poetry.dependencies

    @property
    def dev_dependencies(self):
        return self.pysenv.dev_dependencies or self.tool.poetry.dev_dependencies

    @property
    def version(self):
        return self.pysenv.version or self.tool.poetry.version

    @property
    def description(self):
        return self.pysenv.description or self.tool.poetry.description

    @property
    def package_name(self):
        return self.pysenv.name or self.tool.poetry.name

    @property
    def homepage(self):
        return self.pysenv.homepage or self.tool.poetry.homepage or "__NONE__"

    @property
    def authors(self):
        return self.pysenv.authors or self.tool.poetry.authors

    @property
    def python_version(self):
        return self.dependencies.get("python", None)

    def venv_name(self):
        return self.pysenv.venv.name or self.package_name

    @property
    def conda_path(self):
        return self.pysenv.conda_path or ensureconda(no_install=True)

    @property
    def poetry_path(self):
        return self.pysenv.poetry_path or shutil.which("poetry")

    def validate_fields(self):
        if self.poetry_path is None:
            log.warn(
                "No poetry executable found. "
                "Add poetry to your PATH or define it in the pyproject.toml"
                " with key 'tool.pysenv.poetry_path'"
            )
        if self.conda_path is None:
            log.warn(
                "No conda executable found. "
                "Add conda to your PATH or define it in the pyproject.toml"
                " with key 'tool.pysenv.conda_path'"
            )
        # todo add more validations
