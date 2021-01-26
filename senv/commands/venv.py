import subprocess
from os import environ
from typing import List

import typer

from senv.command_lambdas import get_conda_platforms, get_default_build_system
from senv.log import log
from senv.pyproject import BuildSystem, PyProject
from senv.pyproject_to_conda import (
    generate_combined_conda_lock_file,
    pyproject_to_conda_venv_dict,
)
from senv.shell import SenvShell
from senv.utils import cd, mock_conda_resolver

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
    c = PyProject.get()
    if build_system == BuildSystem.POETRY:
        with cd(c.config_path.parent):
            subprocess.check_call([c.poetry_path, "install", "--remove-untracked"])
    elif build_system == BuildSystem.CONDA:
        if not c.venv.conda_venv_lock_path.exists():
            log.info("No lock file found, locking environment now")
            lock(build_system=build_system, platforms=get_conda_platforms())
        log.info(f"Syncing environment {c.venv.name}")
        with c.venv.platform_conda_lock as lock_file:
            result = subprocess.run(
                [
                    str(c.conda_path),
                    "create",
                    "--file",
                    str(lock_file.resolve()),
                    "--yes",
                    "--name",
                    c.venv.name,
                ]
            )
        if result.returncode != 0:
            raise typer.Abort("Failed syncing environment")
    else:
        raise NotImplementedError()

    typer.echo("Activate the environment with `senv venv shell`")


@app.command()
def shell(build_system: BuildSystem = typer.Option(get_default_build_system)):
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
    minimized_versions: bool = typer.Option(
        False,
    ),
):
    c = PyProject.get()
    if build_system == BuildSystem.POETRY:
        if minimized_versions:
            raise NotImplementedError(
                "minimized_versions locking system not implemented for poetry yet"
            )
        with cd(c.config_path.parent):
            subprocess.check_call([c.poetry_path, "lock"])
    elif build_system == BuildSystem.CONDA:
        if minimized_versions:
            from conda.api import Solver
            from conda.models.channel import Channel

            with mock_conda_resolver():
                solver = Solver(
                    "/home/jirazabal/conda_poc2",
                    (Channel("conda-forge"),),
                    specs_to_add=("typer",),
                )
                txn = solver.solve_final_state()
            print(txn)
        else:
            log.info("Building conda env from pyproject.toml")
            c.venv.conda_venv_lock_path.parent.mkdir(exist_ok=True, parents=True)
            combined_lock = generate_combined_conda_lock_file(
                platforms,
                pyproject_to_conda_venv_dict(),
            )
            c.venv.conda_venv_lock_path.write_text(combined_lock.json(indent=2))
            log.info("lock file updated, sync environment running `senv venv sync`")
    else:
        raise NotImplementedError()
