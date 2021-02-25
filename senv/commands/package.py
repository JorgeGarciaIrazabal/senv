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
    generate_app_lock_file_based_on_tested_lock_path,
    publish_conda,
    set_conda_build_path,
)
from senv.log import log
from senv.pyproject import BuildSystem, PyProject
from senv.pyproject_to_conda import (
    generate_combined_conda_lock_file,
    pyproject_to_recipe_yaml,
)
from senv.utils import auto_confirm_yes, build_yes_option, cd, tmp_env

app = typer.Typer(add_completion=False)


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
            set_conda_build_path()
            args = ["conda-mambabuild", "--override-channels"]
            for c in PyProject.get().senv.conda_channels:
                args += ["--channel", c]
            meta_path = (
                PyProject.get().config_path.parent / "conda.recipe" / "meta.yaml"
            )
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
    based_on_tested_lock_file: Optional[Path] = typer.Option(
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
    c = PyProject.get()
    platforms = platforms
    if build_system == BuildSystem.POETRY:
        raise NotImplementedError()
    elif build_system == BuildSystem.CONDA:
        c.senv.package.conda_lock_path.parent.mkdir(exist_ok=True, parents=True)
        if based_on_tested_lock_file is None:
            combined_lock = generate_combined_conda_lock_file(
                platforms,
                dict(
                    name=c.package_name,
                    channels=conda_channels,
                    dependencies={c.package_name: f"=={c.version}"},
                ),
            )
            c.senv.package.conda_lock_path.write_text(combined_lock.json(indent=2))

        else:
            combined_lock = generate_app_lock_file_based_on_tested_lock_path(
                lock_path=based_on_tested_lock_file,
                conda_channels=conda_channels,
                platforms=platforms,
            )

            c.senv.package.conda_lock_path.write_text(combined_lock.json(indent=2))
        log.info(
            f"Package lock file generated in {c.senv.package.conda_lock_path.resolve()}"
        )
    else:
        raise NotImplementedError()
