import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Optional

import typer
from tomlkit.exceptions import NonExistentKey

from senv.command_lambdas import (
    get_conda_channels,
    get_conda_platforms,
    get_default_build_system,
)
from senv.commands.settings_writer import remove_config_value_from_pyproject
from senv.conda_publish import (
    build_lock_paths,
    ensure_conda_build,
    generate_app_lock_file_based_on_tested_lock_path,
    lock_file_with_metadata,
    publish_conda,
    set_conda_build_path,
)
from senv.pyproject import BuildSystem, PyProject
from senv.pyproject_to_conda import pyproject_to_env_app_yaml, pyproject_to_recipe_yaml
from senv.utils import cd, tmp_env, tmp_repo

app = typer.Typer(add_completion=False)


@app.command(name="build")
def build_package(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    python_version: Optional[str] = None,
):
    # todo add progress bar
    if build_system == BuildSystem.POETRY:
        with cd(PyProject.get().config_path.parent):
            subprocess.check_call([PyProject.get().poetry_path, "build"])
    elif build_system == BuildSystem.CONDA:
        conda_build_path = ensure_conda_build()
        with tmp_env(), tmp_repo() as config:
            set_conda_build_path()
            # removing build-system from pyproject.toml as conda doesn't like it
            # when building the package
            try:
                remove_config_value_from_pyproject(config.config_path, "build-system")
            except NonExistentKey:
                pass
            args = [conda_build_path, "--no-test"]
            for c in PyProject.get().senv.conda_channels:
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
        with cd(PyProject.get().config_path.parent):
            repository_url = (
                repository_url or PyProject.get().senv.poetry_publish_repository
            )
            if repository_url is not None:
                subprocess.check_call(
                    [
                        PyProject.get().poetry_path,
                        "config",
                        f"repositories.senv_{PyProject.get().package_name}",
                        repository_url,
                    ]
                )
            args = [PyProject.get().poetry_path, "publish"]
            if username and password:
                args += ["--username", username, "--password", password]
            subprocess.check_call(args)
    elif build_system == BuildSystem.CONDA:
        with cd(PyProject.get().config_path.parent):
            repository_url = (
                repository_url or PyProject.get().senv.conda_publish_channel
            )
            # todo, this is super specific to our case, we need to make this more generic
            if repository_url is None:
                raise NotImplementedError(
                    "repository_url is required to publish a conda environment. "
                    "Only private channels are currently allowed"
                )
            publish_conda(username, password, repository_url)
    else:
        raise NotImplementedError()


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
        PyProject.get().senv.package_lock_dir.mkdir(exist_ok=True, parents=True)
        if based_on_tested_lock_files_template is None:
            with cd(
                PyProject.get().senv.package_lock_dir
            ), TemporaryDirectory() as tmp_dir:
                env_app_yaml = pyproject_to_env_app_yaml(
                    channels=conda_channels,
                    output=Path(tmp_dir) / "env.yaml",
                )
                lock_file_with_metadata(
                    [env_app_yaml],
                    conda_exe=PyProject.get().senv.conda_path,
                    platforms=platforms,
                )
        else:
            lock_paths = build_lock_paths(
                based_on_tested_lock_files_template, platforms
            )

            for platform, path in lock_paths.items():
                generate_app_lock_file_based_on_tested_lock_path(
                    platform, path, conda_channels
                )

    else:
        raise NotImplementedError()
