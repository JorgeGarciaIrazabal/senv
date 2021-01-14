import os
import subprocess
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import List, Optional

import requests
import typer
from conda_lock.conda_lock import run_lock
from conda_lock.src_parser.pyproject_toml import normalize_pypi_name
from tomlkit.exceptions import NonExistentKey

from senv.command_lambdas import (
    get_conda_channels,
    get_conda_platforms,
    get_default_build_system,
)
from senv.commands.settings_writer import (
    remove_config_value_from_pyproject,
)
from senv.config import BuildSystem, Config
from senv.errors import SenvError, SenvNotAllRequiredLockFiles
from senv.log import log
from senv.pyproject_to_conda import (
    create_env_yaml,
    pyproject_to_env_app_yaml,
    pyproject_to_recipe_yaml,
)
from senv.utils import cd, tmp_env, tmp_repo

app = typer.Typer()


def _ensure_conda_build():
    if which("conda-build") is None:
        log.warning("conda build not found, install conda-build")
        if typer.confirm("Do you want to install it?"):
            log.info("Installing conda-build")
            subprocess.check_call(
                [
                    Config.get().conda_path,
                    "install",
                    "conda-build",
                    "-c",
                    "conda-forge",
                    "-y",
                ]
            )
            return subprocess.check_output(
                [Config.get().conda_path, "run", "which", "conda-build"]
            ).strip()
        else:
            raise typer.Abort()
    return which("conda-build")


def _set_conda_build_path():
    Config.get().senv.conda_build_path.mkdir(parents=True, exist_ok=True)
    os.environ["CONDA_BLD_PATH"] = str(Config.get().senv.conda_build_path)


@app.command(name="build")
def build_package(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    python_version: Optional[str] = None,
):
    # todo add progress bar
    if build_system == BuildSystem.POETRY:
        with cd(Config.get().config_path.parent):
            subprocess.check_call([Config.get().poetry_path, "build"])
    elif build_system == BuildSystem.CONDA:
        conda_build_path = _ensure_conda_build()
        with tmp_env(), tmp_repo() as config:
            _set_conda_build_path()
            # removing build-system from pyproject.toml as conda doesn't like it
            # when building the package
            try:
                remove_config_value_from_pyproject(config.config_path, "build-system")
            except NonExistentKey as e:
                pass
            args = [conda_build_path, "--no-test"]
            for c in Config.get().senv.conda_channels:
                args += ["-c", c]
            meta_path = config.config_path.parent / "conda.recipe" / "meta.yaml"
            pyproject_to_recipe_yaml(
                python_version=python_version,
                output=meta_path,
            )
            if python_version:
                args.extend(["--python", python_version])
            result = subprocess.run(args + [str(meta_path.parent)])
            if result.returncode != 0:
                raise typer.Abort("Failed building conda package")
    else:
        raise NotImplementedError()


def _publish_conda(username: str, password: str, repository_url: str):
    conda_dist = Config.get().senv.conda_build_path
    for tar_path in conda_dist.glob(f"*/{Config.get().package_name}*.tar.bz2"):
        package = tar_path.name
        arch = tar_path.parent.name
        dest = f"{repository_url}/{arch}/{package}"
        resp = requests.head(dest)
        if resp.status_code == 404:
            log.warning("Object already exists not reuploading...")
        else:
            subprocess.check_call(
                [
                    "curl",
                    f"-u{username}:{password}",
                    "-T",
                    str(tar_path.resolve()),
                    dest,
                ],
            )


@app.command(name="publish")
def publish_package(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    python_version: Optional[str] = None,
    build: bool = False,
    repository_url: Optional[str] = None,
    username: str = typer.Option(None, envvar="SENV_PUBLISHER_USERNAME"),
    password: str = typer.Option(None, envvar="SENV_PUBLISHER_PASSWORD"),
):
    if build:
        build_package(build_system=build_system, python_version=python_version)
    if build_system == BuildSystem.POETRY:
        with cd(Config.get().config_path.parent):
            repository_url = (
                repository_url or Config.get().senv.poetry_publish_repository
            )
            if repository_url is not None:
                subprocess.check_call(
                    [
                        Config.get().poetry_path,
                        "config",
                        f"repositories.senv_{Config.get().package_name}",
                        repository_url,
                    ]
                )
            args = [Config.get().poetry_path, "publish"]
            if username and password:
                args += ["--username", username, "--password", password]
            subprocess.check_call(args)
    elif build_system == BuildSystem.CONDA:
        with cd(Config.get().config_path.parent):
            repository_url = repository_url or Config.get().senv.conda_publish_channel
            # todo, this is super specific to our case, we need to make this more generic
            if repository_url is None:
                raise NotImplementedError(
                    "repository_url is required to publish a conda environment. "
                    "Only private channels are currently allowed"
                )
            _publish_conda(username, password, repository_url)
    else:
        raise NotImplementedError()


def build_lock_paths(based_on_tested_lock_files_template, platforms):
    lock_paths = {}
    if "{platform}" not in based_on_tested_lock_files_template:
        raise SenvError("no {platform} in 'based_on_tested_lock_files_template'")
    for platform in platforms:
        lock_paths[platform] = Path(
            based_on_tested_lock_files_template.replace("{platform}", platform)
        )
    missing_lock_files = [p for p in lock_paths.values() if not p.exists()]

    if len(missing_lock_files) > 0:
        raise SenvNotAllRequiredLockFiles(missing_lock_files)
    return lock_paths


def _generate_app_lock_file_based_on_tested_lock_path(
    platform, lock_path, direct_dependencies_name, conda_channels
):
    with cd(Config.get().senv.package_lock_dir), TemporaryDirectory() as tmp_dir:
        lock_str = lock_path.read_text()
        lock_str = lock_str.split("@EXPLICIT", 1)[1].strip()
        # add the current package
        dependencies = {
            Config.get().package_name: f"=={Config.get().version}",
        }
        for line in lock_str.splitlines(keepends=False):
            channel, dep = line.rsplit("/", 1)
            name, version, _ = dep.rsplit("-", 2)
            if name.lower() in direct_dependencies_name:
                dependencies[name] = f"=={version}"
        yaml_path = create_env_yaml(
            channels=conda_channels,
            output=Path(tmp_dir) / "env.yaml",
            dependencies=dependencies,
        )
        run_lock(
            [yaml_path],
            conda_exe=Config.get().conda_path,
            platforms=[platform],
        )


@app.command(name="lock")
def lock_app(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    platforms: List[str] = typer.Option(
        get_conda_platforms,
        case_sensitive=False,
        help="conda platforms, for example osx-64 and/or linux-64",
    ),
    based_on_tested_lock_files_template: Optional[str] = typer.Option(
        None,
        help="Create the lock file with the same direct dependencies"
        " as the ones pinned in the lock template provided.\n"
        "For conda locks, this template should include `{platform}`"
        " so each platform output can be based on the right lock file.\n"
        "More information in {Todo: add link to documentation}",
    ),
    conda_channels: Optional[List[str]] = typer.Option(
        get_conda_channels,
    ),
):
    platforms = platforms
    if build_system == BuildSystem.POETRY:
        raise NotImplementedError()
    elif build_system == BuildSystem.CONDA:
        Config.get().senv.package_lock_dir.mkdir(exist_ok=True, parents=True)
        if based_on_tested_lock_files_template is None:
            with cd(
                Config.get().senv.package_lock_dir
            ), TemporaryDirectory() as tmp_dir:
                env_app_yaml = pyproject_to_env_app_yaml(
                    channels=conda_channels,
                    output=Path(tmp_dir) / "env.yaml",
                )
                run_lock(
                    [env_app_yaml],
                    conda_exe=Config.get().conda_path,
                    platforms=platforms,
                )
        else:
            lock_paths = build_lock_paths(
                based_on_tested_lock_files_template, platforms
            )
            direct_dependencies_name = {
                normalize_pypi_name(d).lower() for d in Config.get().dependencies.keys()
            }
            # always include python even if it is not in the dependencies
            direct_dependencies_name.add("python")

            for platform, path in lock_paths.items():
                _generate_app_lock_file_based_on_tested_lock_path(
                    platform, path, direct_dependencies_name, conda_channels
                )

    else:
        raise NotImplementedError()
