import os
import shutil
from contextlib import contextmanager
from copy import deepcopy
from enum import Enum
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional, Set

import toml
from conda_lock.conda_lock import DEFAULT_PLATFORMS
from ensureconda import ensureconda
from pydantic import BaseModel, Field, PrivateAttr, root_validator, validator
from senvx.constants import LOCKED_PACKAGE_SUFFIX

from senv.errors import SenvBadConfiguration
from senv.log import log
from senvx.models import CombinedCondaLock
from senv.utils import get_current_platform


class BuildSystem(str, Enum):
    CONDA = "conda"
    POETRY = "poetry"


class _SenvEnv(BaseModel):
    build_system: Optional[BuildSystem] = Field(
        None,
        alias="build-system",
        description="Default system used to build the virtual environment."
        " (If not defined, use tool.senv.build_system)",
    )
    conda_lock_platforms: Set[str] = Field(
        set(DEFAULT_PLATFORMS),
        alias="conda-lock-platforms",
        description="(Conda only) Default set of platforms to solve and lock the dependencies for",
    )
    conda_lock_path: Path = Field(
        Path("conda_env.lock.json"),
        alias="conda-lock-path",
        description="(Conda only) The path of where the lock file will be generated",
    )
    name: Optional[str] = Field(
        None,
        description="(Conda only) Alternative name for the conda environment"
        " (by default: tool.senv.name)",
    )

    @property
    @contextmanager
    def platform_conda_lock(self) -> Path:
        """
        Creates a temporary lock file that conda-lock can understand for the current platform
        :return: the path of the conda lock file
        """
        plat = get_current_platform()

        if not self.conda_lock_path.exists():
            raise SenvBadConfiguration(
                f"No conda env lock file found in {self.conda_lock_path.resolve()}"
            )

        with TemporaryDirectory() as tmp_dir:
            combine_lock_file = CombinedCondaLock.parse_file(self.conda_lock_path)
            plat_file = Path(tmp_dir) / f"plat-{plat}.lock"
            plat_file.write_text(
                "@EXPLICIT\n" + "\n".join(combine_lock_file.platform_tar_links[plat])
            )
            yield plat_file


class _SenvPackage(BaseModel):
    build_system: Optional[BuildSystem] = Field(
        None,
        alias="build-system",
        description="Default system used to build the final package."
        " (If not defined, use tool.senv.build_system)",
    )
    conda_build_path: Path = Field(
        None, alias="conda-build-path", env="SENV_CONDA_BUILD_PATH"
    )
    conda_publish_url: Optional[str] = Field(
        "https://anaconda.org",
        alias="conda-publish-channel",
        env="SENV_CONDA_PUBLISH_URL",
    )
    conda_lock_path: Path = Field(
        Path("package_locked.lock.json"), alias="conda-lock-path"
    )
    poetry_publish_repository: Optional[str] = Field(
        None, alias="poetry-publish-repository", env="SENV_POETRY_PUBLISH_REPOSITORY"
    )


class _Senv(BaseModel):
    env: _SenvEnv = Field(_SenvEnv())
    package: _SenvPackage = Field(_SenvPackage())
    build_system: Optional[BuildSystem] = Field(
        BuildSystem.CONDA,
        alias="build-system",
        description="Default system used to build the virtual environment and the package",
    )
    # poetry shared
    name: Optional[str] = Field(None, description="The name of the package")
    version: Optional[str] = Field(None, description="The version of the package")
    description: Optional[str] = Field(
        None, description="A short description of the package"
    )
    license: str = Field(
        "Proprietary",
        description="License of the package."
        " License identifiers are listed at [SPDX](https://spdx.org/licenses/)",
    )
    authors: Optional[List[str]] = Field(
        None,
        description="The authors of the package. Authors must be in the form `name <email>`",
    )
    readme: Optional[str] = Field(
        None,
        description="(Poetry only) The readme file of the package."
        " The file can be either `README.rst` or `README.md`",
    )
    homepage: Optional[str] = Field(
        None, description="An URL to the website of the project"
    )
    repository: Optional[str] = Field(
        None, description="An URL to the repository of the project"
    )
    documentation: Optional[str] = Field(
        None, description="An URL to the documentation of the project"
    )
    keywords: Optional[List[str]] = Field(
        None,
        description="(Poetry only) A list of keywords (max: 5) that the package is related to",
    )
    classifiers: Optional[List[str]] = Field(
        None,
        description="(Poetry only) A list of PyPI "
        "[trove classifiers](https://pypi.org/classifiers/) that describe the project",
    )
    packages: Optional[Dict[str, str]] = Field(
        None,
        description="(Poetry Only) A list of packages"
        " and modules to include in the final distribution",
    )
    include: Optional[List[str]] = Field(
        None,
        description="A list of patterns that will be included in the final package",
    )
    # todo
    # exclude: Optional[List[str]] = Field(
    #     None,
    #     description="A list of patterns that will be excluded in the final package",
    # )

    dependencies: Dict[str, Any] = Field(
        default_factory=dict,
        description="List of dependencies to be included in the "
        "final package and in the virtual environment",
    )
    dev_dependencies: Dict[str, Any] = Field(
        default_factory=dict,
        alias="dev-dependencies",
        description="List of dependencies to be included in the "
        "virtual environment but not in the final package",
    )
    scripts: Dict[str, str] = Field(
        default_factory=dict,
        description="The scripts or executables that will be installed when installing the package",
    )

    # senv specific
    conda_channels: Optional[List[str]] = Field(
        [],
        alias="conda-channels",
        description="(Conda Only) The conda channels to build the "
        "package and the virtual environment",
    )
    conda_path: Optional[Path] = Field(
        None,
        alias="conda-path",
        env="SENV_CONDA_PATH",
        description="(Conda Only) path of the conda executable."
        " (If not defined, it will try to find it in PATH)",
    )
    poetry_path: Optional[Path] = Field(
        None,
        alias="poetry-path",
        env="SENV_POETRY_PATH",
        description="(Poetry Only) path of the poetry executable."
        " (If not defined, it will try to find it in PATH)",
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        # if not build_system in env or package, then use the generic one
        if self.env.build_system is None:
            self.env.build_system = self.build_system
        if self.package.build_system is None:
            self.package.build_system = self.build_system

    @validator("conda_path", "poetry_path")
    def _validate_executable(cls, p: Path):
        if not p.exists():
            resolved_p = which(p)
            if resolved_p is None:
                raise ValueError(f"Provided path {p} was not found")
            else:
                p = Path(resolved_p).resolve()
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
        if self.senv.package.conda_build_path is None:
            self.senv.package.conda_build_path = (
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
    def env_name_defaults_to_package_name(cls, values: Dict[str, Any]):
        if len(values) == 0:
            # it is likely that another validation failed before this one
            return values
        tool: _Tool = values.get("tool")
        tool.senv.env.name = tool.senv.env.name or tool.senv.name
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
    def env(self) -> _SenvEnv:
        return self.tool.senv.env

    @property
    def version(self) -> str:
        return self.senv.version

    @property
    def package_name(self) -> str:
        return self.senv.name

    @property
    def package_name_locked(self) -> str:
        return f"{self.package_name}{LOCKED_PACKAGE_SUFFIX}"

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

        if self.senv.package.conda_build_path is None:
            raise SenvBadConfiguration("conda_build_root can not be None")

        try:
            self.senv.package.conda_build_path.resolve().relative_to(
                self.config_path.parent.resolve()
            )
            raise SenvBadConfiguration(
                "conda-build-path can not be a subdirectory of the project's directory"
            )
        except ValueError:
            pass

        # todo add more validations
