import os.path
import subprocess
from os import environ
import shlex
from typing import List

import typer

from senv.command_lambdas import get_conda_platforms, get_default_env_build_system
from senv.log import log
from senv.pyproject import BuildSystem, PyProject
from senv.pyproject_to_conda import (
    generate_combined_conda_lock_file,
    pyproject_to_conda_env_dict,
)
from senv.shell import spawn_shell
from senv.utils import cd

app = typer.Typer(add_completion=False)


@app.command(
    short_help="Install the dependencies and the dev-dependencies in a virtual environment",
    help="""
    Installs both, the dependencies and the dev-dependencies in a a virtual environment. 
    This env van be activated with `senv env shell`.
    You can configure where the lock files will be stored with the key `tools.senv.env.env-lock-dir
    """,
)
def install(build_system: BuildSystem = typer.Option(get_default_env_build_system)):
    sync(build_system=build_system)


@app.command(
    short_help="Updates the lock files and install the dependencies in your env",
    help="""
    Updates the lock files and install the dependencies in your env based on the constrains defined in the pyproject.toml
    """,
)
def update(
    build_system: BuildSystem = typer.Option(get_default_env_build_system),
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
    short_help="Syncs the current env with the lock files",
    help="""
    Syncs the current env with the lock files. Installs the missing dependencies and removes the ones that are not in the lock file
    """,
)
def sync(build_system: BuildSystem = typer.Option(get_default_env_build_system)):
    c = PyProject.get()
    if build_system == BuildSystem.POETRY:
        with cd(c.config_path.parent):
            subprocess.check_call([c.poetry_path, "install", "--remove-untracked"])
    elif build_system == BuildSystem.CONDA:
        if not c.env.conda_lock_path.exists():
            log.info("No lock file found, locking environment now")
            lock(build_system=build_system, platforms=get_conda_platforms())
        with c.env.platform_conda_lock as lock_file:
            result = subprocess.run(
                [
                    str(c.conda_path),
                    "create",
                    "--file",
                    str(lock_file.resolve()),
                    "--yes",
                    "--name",
                    c.env.name,
                ]
            )
        if result.returncode != 0:
            raise typer.Abort("Failed syncing environment")
    else:
        raise NotImplementedError()


@app.command()
def shell(build_system: BuildSystem = typer.Option(get_default_env_build_system)):
    c = PyProject.get()
    # conda activate does not work using the conda executable path (I am not sure why)
    # force adding the conda executable to the path and then call it
    environ["PATH"] = f"{c.conda_path.parent}{os.path.pathsep}{environ.get('PATH')}"
    if build_system == BuildSystem.POETRY:
        cwd = os.getcwd()
        with cd(c.config_path.parent):
            with spawn_shell(command="poetry shell", cwd=cwd):
                pass

    elif build_system == BuildSystem.CONDA:
        with spawn_shell(
            command=f"{shlex.quote(str(c.conda_path.name))} activate {c.env.name}",
        ):
            pass
    else:
        raise NotImplementedError()
    environ["PATH"] = os.path.pathsep.join(
        environ.get("PATH").split(os.path.pathsep)[1:]
    )


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def run(
    ctx: typer.Context,
    build_system: BuildSystem = typer.Option(get_default_env_build_system),
):
    if build_system == BuildSystem.POETRY:
        with cd(PyProject.get().config_path.parent):
            subprocess.check_call(["poetry", "run"] + ctx.args)
    elif build_system == BuildSystem.CONDA:
        subprocess.check_call(
            [
                "conda",
                "run",
                "-n",
                PyProject.get().env.name,
                "--no-capture-output",
                "--live-stream",
            ]
            + ctx.args
        )
    else:
        raise NotImplementedError()


@app.command()
def lock(
    build_system: BuildSystem = typer.Option(get_default_env_build_system),
    platforms: List[str] = typer.Option(
        get_conda_platforms,
        case_sensitive=False,
        help="conda platforms, for example osx-64 or linux-64",
    ),
):
    c = PyProject.get()
    if build_system == BuildSystem.POETRY:
        with cd(c.config_path.parent):
            subprocess.check_call([c.poetry_path, "lock"])
    elif build_system == BuildSystem.CONDA:
        c.env.conda_lock_path.parent.mkdir(exist_ok=True, parents=True)
        combined_lock = generate_combined_conda_lock_file(
            platforms,
            pyproject_to_conda_env_dict(),
        )
        c.env.conda_lock_path.write_text(combined_lock.json(indent=2))
    else:
        raise NotImplementedError()
