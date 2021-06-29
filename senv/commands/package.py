import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

import typer

from senv.command_lambdas import (
    get_conda_channels,
    get_conda_platforms,
    get_default_package_build_system,
)
from senv.conda_publish import (
    build_conda_package_from_recipe,
    generate_app_lock_file_based_on_tested_lock_path,
    publish_conda,
)
from senv.log import log
from senv.pyproject import BuildSystem, PyProject
from senv.pyproject_to_conda import (
    generate_combined_conda_lock_file,
    locked_package_to_recipe_yaml,
    pyproject_to_recipe_yaml,
)
from senv.utils import auto_confirm_yes, build_yes_option, cd, cd_tmp_dir, tmp_env

app = typer.Typer(add_completion=False)

based_on_tested_lock_file_option = typer.Option(
    None,
    help="Create the lock file with the same direct dependencies"
    " as the ones pinned in the lock template provided.\n"
    "For conda locks, this template should include `{platform}`"
    " so each platform output can be based on the right lock file.\n"
    "More information in {Todo: add link to documentation}",
)


@app.command(name="build")
def build_package(
    build_system: BuildSystem = typer.Option(get_default_package_build_system),
    python_version: Optional[str] = None,
):
    # todo add progress bar
    if build_system == BuildSystem.POETRY:
        with cd(PyProject.get().config_path.parent):
            subprocess.check_call([PyProject.get().poetry_path, "build"])
    elif build_system == BuildSystem.CONDA:
        with tmp_env():
            meta_path = (
                PyProject.get().config_path.parent / "conda.recipe" / "meta.yaml"
            )
            pyproject_to_recipe_yaml(
                python_version=python_version,
                output=meta_path,
            )
            build_conda_package_from_recipe(meta_path, python_version)
    else:
        raise NotImplementedError()


@app.command(name="publish")
def publish_package(
    build_system: BuildSystem = typer.Option(get_default_package_build_system),
    python_version: Optional[str] = None,
    build: bool = typer.Option(False, "--build", "-b"),
    repository_url: Optional[str] = None,
    username: str = typer.Option(
        ..., "--username", "-u", envvar="SENV_PUBLISHER_USERNAME"
    ),
    password: str = typer.Option(
        ..., "--password", "-p", envvar="SENV_PUBLISHER_PASSWORD"
    ),
    yes: bool = build_yes_option(),
):
    with auto_confirm_yes(yes):
        if build:
            build_package(build_system=build_system, python_version=python_version)
        if build_system == BuildSystem.POETRY:
            with cd(PyProject.get().config_path.parent):
                repository_url = (
                    repository_url
                    or PyProject.get().senv.package.poetry_publish_repository
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
                    repository_url or PyProject.get().senv.package.conda_publish_url
                )
                if repository_url is None:
                    # todo add logic to publish to conda-forge
                    raise NotImplementedError(
                        "repository_url is required to publish a conda environment. "
                    )
                publish_conda(username, password, repository_url)
        else:
            raise NotImplementedError()


@app.command(name="lock")
def lock_app(
    build_system: BuildSystem = typer.Option(get_default_package_build_system),
    platforms: List[str] = typer.Option(
        get_conda_platforms,
        case_sensitive=False,
        help="conda platforms, for example osx-64 and/or linux-64",
    ),
    based_on_tested_lock_file: Optional[Path] = based_on_tested_lock_file_option,
    conda_channels: Optional[List[str]] = typer.Option(
        get_conda_channels,
    ),
    output: Path = typer.Option(
        lambda: PyProject.get().senv.package.conda_lock_path, "--output", "-o"
    ),
):
    c = PyProject.get()
    platforms = platforms
    if build_system == BuildSystem.POETRY:
        raise NotImplementedError()
    elif build_system == BuildSystem.CONDA:
        output.parent.mkdir(exist_ok=True, parents=True)
        if based_on_tested_lock_file is None:
            combined_lock = generate_combined_conda_lock_file(
                platforms,
                dict(
                    name=c.package_name,
                    channels=conda_channels,
                    dependencies={c.package_name: f"=={c.version}"},
                ),
            )
            output.write_text(combined_lock.json(indent=2))

        else:
            combined_lock = generate_app_lock_file_based_on_tested_lock_path(
                lock_path=based_on_tested_lock_file,
                conda_channels=conda_channels,
                platforms=platforms,
            )

            output.write_text(combined_lock.json(indent=2))
        log.info(f"Package lock file generated in {output.resolve()}")
    else:
        raise NotImplementedError()


@app.command(name="publish-locked")
def publish_locked_package(
    build_system: BuildSystem = typer.Option(get_default_package_build_system),
    repository_url: Optional[str] = None,
    username: str = typer.Option(
        ..., "--username", "-u", envvar="SENV_PUBLISHER_USERNAME"
    ),
    password: str = typer.Option(
        ..., "--password", "-p", envvar="SENV_PUBLISHER_PASSWORD"
    ),
    lock_file: Path = typer.Option(
        lambda: PyProject.get().senv.package.conda_lock_path,
        "--lock-file",
        "-l",
        exists=True,
    ),
    yes: bool = build_yes_option(),
):
    c: PyProject = PyProject.get()
    with auto_confirm_yes(yes):
        if build_system == BuildSystem.POETRY:
            raise NotImplementedError("publish locked ")
        elif build_system == BuildSystem.CONDA:
            with cd_tmp_dir() as tmp_dir:
                meta_path = tmp_dir / "conda.recipe" / "meta.yaml"
                temp_lock_path = meta_path.parent / "package_locked_file.lock.json"
                meta_path.parent.mkdir(parents=True)
                shutil.copyfile(
                    str(lock_file.absolute()), str(temp_lock_path.absolute())
                )

                locked_package_to_recipe_yaml(temp_lock_path, meta_path)
                build_conda_package_from_recipe(meta_path.absolute())

                with cd(meta_path.parent):
                    repository_url = repository_url or c.senv.package.conda_publish_url
                    publish_conda(
                        username,
                        password,
                        repository_url,
                        package_name=c.package_name_locked,
                    )
        else:
            raise NotImplementedError()
