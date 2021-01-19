import subprocess
from os import environ
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

import typer
import yaml
from conda_lock.conda_lock import run_lock

from senv.command_lambdas import get_conda_platforms, get_default_build_system
from senv.log import log
from senv.pyproject import BuildSystem, PyProject
from senv.pyproject_to_conda import pyproject_to_conda_venv_dict
from senv.shell import SenvShell
from senv.utils import cd

app = typer.Typer(add_completion=False)


@app.command(
    short_help="Install the dependencies and the dev-dependencies in a virtual environment",
    help="""
    Installs both, the dependencies and the dev-dependencies in a a virtual environment. 
    This venv van be activated with `senv venv shell`.
    You can configure where the lock files will be stored with the key `tools.senv.venv.venv-lock-dir
    """,
)
def install(build_system: BuildSystem = typer.Option(get_default_build_system)):
    sync(build_system=build_system)


@app.command(
    short_help="Updates the lock files and install the dependencies in your venv",
    help="""
    Updates the lock files and install the dependencies in your venv based on the constrains defined in the pyproject.toml
    """,
)
def update(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    platforms: List[str] = typer.Option(
        get_conda_platforms,
        case_sensitive=False,
        help="conda platforms, for example osx-64 or linux-64",
    ),
):
    if build_system == BuildSystem.POETRY:
        with cd(PyProject.get().config_path.parent):
            subprocess.check_call([PyProject.get().poetry_path, "update"])
    elif build_system == BuildSystem.CONDA:
        lock(build_system=build_system, platforms=platforms)
        sync(build_system=build_system)

    else:
        raise NotImplementedError()


@app.command(
    short_help="Syncs the current venv with the lock files",
    help="""
    Syncs the current venv with the lock files. Installs the missing dependencies and removes the ones that are not in the lock file
    """,
)
def sync(build_system: BuildSystem = typer.Option(get_default_build_system)):
    if build_system == BuildSystem.POETRY:
        with cd(PyProject.get().config_path.parent):
            subprocess.check_call(
                [PyProject.get().poetry_path, "install", "--remove-untracked"]
            )
    elif build_system == BuildSystem.CONDA:
        if not PyProject.get().venv.platform_conda_lock.exists():
            log.info("No lock file found, locking environment now")
            lock(build_system=build_system, platforms=get_conda_platforms())
        log.info(f"Syncing environment {PyProject.get().venv.name}")
        result = subprocess.run(
            [
                str(PyProject.get().conda_path),
                "create",
                "--file",
                str(PyProject.get().venv.platform_conda_lock),
                "--yes",
                "--name",
                PyProject.get().venv.name,
            ]
        )
        if result.returncode != 0:
            raise typer.Abort("Failed syncing environment")
    else:
        raise NotImplementedError()

    typer.echo("Activate the environment with `senv venv shell`")


@app.command()
def shell(build_system: BuildSystem = typer.Option(get_default_build_system)):
    environ["SENV_ACTIVE"] = "1"
    environ["PATH"] = f"{PyProject.get().conda_path.parent}:{environ.get('PATH')}"
    if build_system == BuildSystem.POETRY:
        with cd(PyProject.get().config_path.parent):
            SenvShell.get().activate(command="poetry shell")
    elif build_system == BuildSystem.CONDA:
        SenvShell.get().activate(command=f"conda activate {PyProject.get().venv.name}")
    else:
        raise NotImplementedError()
    environ["PATH"] = ":".join(environ.get("PATH").split(":")[1:])
    environ.pop("SENV_ACTIVE")


@app.command()
def lock(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    platforms: List[str] = typer.Option(
        get_conda_platforms,
        case_sensitive=False,
        help="conda platforms, for example osx-64 or linux-64",
    ),
):
    if build_system == BuildSystem.POETRY:
        with cd(PyProject.get().config_path.parent):
            subprocess.check_call([PyProject.get().poetry_path, "lock"])
    elif build_system == BuildSystem.CONDA:
        log.info("Building conda env from pyproject.toml")
        env_dict = pyproject_to_conda_venv_dict()
        with NamedTemporaryFile(mode="w+") as f:
            PyProject.get().senv.venv.venv_lock_dir.mkdir(exist_ok=True, parents=True)
            with cd(PyProject.get().senv.venv.venv_lock_dir):
                yaml.safe_dump(env_dict, f)
                run_lock(
                    [Path(f.name)],
                    conda_exe=str(PyProject.get().conda_path.resolve()),
                    platforms=platforms,
                )
        log.info("lock files updated, sync environment running `senv venv sync`")
    else:
        raise NotImplementedError()
