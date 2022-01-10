#!/usr/bin/env python
from collections import Mapping
import json
import re
from concurrent.futures import ProcessPoolExecutor
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

import yaml
from conda_lock.conda_lock import run_lock
from conda_lock.src_parser import LockSpecification
from conda_lock.src_parser.pyproject_toml import (
    normalize_pypi_name,
    poetry_version_to_conda_version,
    to_match_spec,
)
from pydantic import BaseModel, Field

from senv.errors import SenvInvalidPythonVersion
from senv.log import log
from senv.pyproject import PyProject
from senvx.models import CombinedCondaLock, LockFileMetaData
from senv.utils import MySpinner, cd_tmp_dir

version_pattern = re.compile("version='(.*)'")

# todo replace with senx constant when we release a new version
LOCKED_PACKAGE_LOCK_NAME = "senv.lock.json"


class _Package(BaseModel):
    name: str
    version: str


class _Source(BaseModel):
    path: Path


class _Build(BaseModel):
    entry_points: List[str] = Field(default_factory=list)
    script: str = Field("python -m pip install --no-deps --ignore-installed -vv .")
    noarch: str = Field("python")


class _Requirements(BaseModel):
    host: List[str]
    run: List[str]


class _About(BaseModel):
    home: Optional[str]
    license: str = Field("INTERNAL")
    summary: Optional[str]
    description: Optional[str]
    dev_url: Optional[str]
    doc_url: Optional[str]
    doc_source_url: Optional[str]


class _Extra(BaseModel):
    maintainers: List[str] = Field(default_factory=list)


class CondaMeta(BaseModel):
    package: _Package
    source: _Source
    build: _Build
    requirements: _Requirements
    about: _About
    extra: _Extra


def _yaml_safe_dump(yaml_dict: Dict, path: Path):
    s = StringIO()
    yaml.safe_dump(yaml_dict, s)
    # need to add `---` to the yaml to fix some issues with conda-build
    # https://github.com/conda/conda-build/issues/3860#issuecomment-740769768
    yaml_str = f"---\n{s.getvalue()}"
    path.write_text(yaml_str)


def _conda_spec_to_conda_build_req(req: str):
    if "[" in req:
        pkg_name, _, specifier = req.partition("[")
        version_match = re.search(version_pattern, specifier)
        assert version_match, req
        version = version_match.group(1)
        return f"{pkg_name} {version}"
    else:
        return req


def _populate_python_version(python_version, dependencies):
    python_req = [r for r in dependencies if r.split()[0] == "python"]
    if len(python_req) == 1:
        if python_version is not None and python_version != python_req[0]:
            log.warning(
                "Python version in the pyproject.toml is different than the one provided"
            )
        elif python_version is None:
            python_version = python_req[0]
    elif python_version is None:
        raise SenvInvalidPythonVersion(
            "No python version provided or defined in pyproject.toml"
        )
    return python_version


# TODO: probably make a Pull request in conda lock to make this logic more accessible
def _parse_pyproject_toml(
    platform: str, include_dev_dependencies: bool
) -> LockSpecification:
    specs: List[str] = []
    deps = PyProject.get().senv.dependencies
    if include_dev_dependencies:
        deps.update(PyProject.get().senv.dev_dependencies)

    for depname, depattrs in deps.items():
        conda_dep_name = normalize_pypi_name(depname)
        if isinstance(depattrs, Mapping):
            poetry_version_spec = depattrs["version"]
            # TODO: support additional features such as markers for things like sys_platform, platform_system
        elif isinstance(depattrs, str):
            poetry_version_spec = depattrs
        else:
            raise TypeError(f"Unsupported type for dependency: {depname}: {depattrs:r}")
        conda_version = poetry_version_to_conda_version(poetry_version_spec)
        spec = to_match_spec(conda_dep_name, conda_version)

        if conda_dep_name == "python":
            specs.insert(0, spec)
        else:
            specs.append(spec)

    return LockSpecification(
        specs=specs, channels=PyProject.get().senv.conda_channels, platform=platform
    )


def _get_dependencies_from_pyproject(include_dev_dependencies):
    lock_spec = _parse_pyproject_toml(
        platform="linux-64",
        include_dev_dependencies=include_dev_dependencies,
    )
    dependencies = [_conda_spec_to_conda_build_req(spec) for spec in lock_spec.specs]
    return dependencies


def pyproject_to_recipe_yaml(
    *,
    python_version: Optional[str] = None,
    output: Path = Path("conda.recipe") / "meta.yaml",
) -> Path:
    meta = pyproject_to_meta(python_version=python_version)
    return meta_to_recipe_yaml(meta=meta, output=output)


def meta_to_recipe_yaml(
    *, meta: CondaMeta, output: Path = Path("conda.recipe") / "meta.yaml"
) -> Path:
    recipe_dir = output.parent
    recipe_dir.mkdir(parents=True, exist_ok=True)
    _yaml_safe_dump(json.loads(meta.json()), output)
    return output


def pyproject_to_meta(
    *,
    python_version: Optional[str] = None,
) -> CondaMeta:
    """
    :param python_version: python version used to create the conda meta file
    """
    dependencies = _get_dependencies_from_pyproject(include_dev_dependencies=False)
    python_version = _populate_python_version(python_version, dependencies)
    if python_version != PyProject.get().python_version:
        log.warning(
            "Python version in the pyproject.toml is different than the one provided"
        )
    if python_version is None:
        raise SenvInvalidPythonVersion(
            f"No python version provided or defined in {PyProject.get().config_path}"
        )

    c: PyProject = PyProject.get()
    license = c.senv.license if c.senv.license != "Proprietary" else "INTERNAL"
    entry_points = [f"{name} = {module}" for name, module in c.senv.scripts.items()]

    return CondaMeta(
        package=_Package(name=c.package_name, version=c.version),
        source=_Source(path=c.config_path.parent.resolve()),
        build=_Build(entry_points=entry_points),
        requirements=_Requirements(
            host=[python_version, "pip", "poetry"], run=dependencies
        ),
        about=_About(
            home=c.senv.homepage,
            license=license,
            description=c.senv.description,
            doc_url=c.senv.documentation,
        ),
        extra=_Extra(maintainers=c.senv.authors),
    )


def pyproject_to_conda_env_dict() -> Dict:
    channels = PyProject.get().senv.conda_channels
    dependencies = _get_dependencies_from_pyproject(include_dev_dependencies=True)

    return dict(
        name=PyProject.get().env.name, channels=channels, dependencies=dependencies
    )


def pyproject_to_env_app_yaml(
    *,
    app_name: Optional[str] = None,
    channels: Optional[List[str]] = None,
    output: Path = Path("app_environment.yaml"),
) -> Path:
    """
    Generates a basic yaml with only it's current version as the dependency
    In order to use it, the package has to be published
    :param app_name: the name of the app,
        by default it will use the name of the package in pyproject.toml
    :param channels: the conda channels needed for the env,
        by default using the channels defined in pyproject.toml
    :param output: where to save the yaml
    :return: output
    """
    c = PyProject.get()
    return create_env_yaml(
        name=app_name,
        channels=channels,
        dependencies={c.package_name: f"=={c.version}"},
        output=output,
    )


def create_env_yaml(
    *,
    dependencies: List[str],
    output: Path,
    name: Optional[str] = None,
    channels: Optional[List[str]] = None,
) -> Path:
    if channels is None:
        channels = []

    c = PyProject.get()
    yaml_dict = dict(
        name=name or c.package_name,
        channels=channels if channels is not None else c.senv.conda_channels,
        dependencies=dependencies,
    )

    recipe_dir = output.parent
    recipe_dir.mkdir(parents=True, exist_ok=True)
    _yaml_safe_dump(yaml_dict, output)
    return output


def combine_conda_lock_files(
    directory: Path, platforms: List[str]
) -> "CombinedCondaLock":
    platform_tar_links = {}
    for platform in platforms:
        lock_file = directory / f"conda-{platform}.lock"
        lock_text = lock_file.read_text()
        clean_lock_test = lock_text.split("@EXPLICIT", 1)[1].strip()
        tar_links = [line.strip() for line in clean_lock_test.splitlines()]
        platform_tar_links[platform] = tar_links
    c = PyProject.get()
    metadata = LockFileMetaData(
        package_name=c.package_name,
        entry_points=list(c.senv.scripts.keys()),
        version=c.version,
    )

    return CombinedCondaLock(metadata=metadata, platform_tar_links=platform_tar_links)


def generate_combined_conda_lock_file(
    platforms: List[str], env_dict: Dict
) -> "CombinedCondaLock":
    c = PyProject.get()
    with NamedTemporaryFile(mode="w+") as f, cd_tmp_dir() as tmp_dir, MySpinner(
        "Building lock files..."
    ) as status:
        status.start()
        yaml.safe_dump(env_dict, f)
        processes = []
        with ProcessPoolExecutor() as executor:
            for platform in platforms:
                p = executor.submit(
                    run_lock,
                    [Path(f.name)],
                    conda_exe=str(c.conda_path.resolve()),
                    platforms=[platform],
                    channel_overrides=env_dict["channels"],
                    kinds=["explicit"],
                )
                processes.append(p)
        status.writeln("combining lock files...")
        return combine_conda_lock_files(tmp_dir, platforms)


def locked_package_to_recipe_yaml(lock_file: Path, output: Path):
    c: PyProject = PyProject.get()
    license_ = c.senv.license if c.senv.license != "Proprietary" else "INTERNAL"
    meta = CondaMeta(
        package=_Package(name=c.package_name_locked, version=c.version),
        build=_Build(
            script=f"mkdir -p $PREFIX && cp {lock_file.resolve()} $PREFIX/{lock_file.name}"
        ),
        source=_Source(path=lock_file.absolute()),
        requirements=_Requirements(host=[], run=[]),
        about=_About(
            home=c.senv.homepage,
            license=license_,
            description=c.senv.description,
            doc_url=c.senv.documentation,
        ),
        extra=_Extra(maintainers=c.senv.authors),
    )

    meta_to_recipe_yaml(meta=meta, output=output)
