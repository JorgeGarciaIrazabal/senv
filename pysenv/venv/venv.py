import subprocess
from os import environ
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List

import typer
import yaml
from conda_lock.conda_lock import do_conda_install, run_lock

from pysenv.command_lambdas import get_conda_platforms, get_default_build_system
from pysenv.log import log
from pysenv.settings.config import BuildSystem, Config
from pysenv.shell import PysenvShell
from pysenv.utils import cd
from pysenv.venv.pyproject_to_conda import pyproject_to_conda_venv_dict

app = typer.Typer()


@app.command()
def install(build_system: BuildSystem = typer.Option(get_default_build_system)):
    sync(build_system=build_system)


@app.command()
def update(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    platforms: List[str] = typer.Option(
        get_conda_platforms,
        case_sensitive=False,
        help="conda platforms, for example osx-64 or linux-64",
    ),
):
    if build_system == BuildSystem.POETRY:
        with cd(Config.get().config_path.parent):
            subprocess.check_call([Config.get().poetry_path, "update"])
    elif build_system == BuildSystem.CONDA:
        lock(build_system=build_system, platforms=platforms)
        sync(build_system=build_system)

    else:
        raise NotImplementedError()


@app.command()
def sync(build_system: BuildSystem = typer.Option(get_default_build_system)):
    if build_system == BuildSystem.POETRY:
        with cd(Config.get().config_path.parent):
            subprocess.check_call([Config.get().poetry_path, "sync"])
    elif build_system == BuildSystem.CONDA:
        if not Config.get().platform_conda_lock.exists():
            log.info("No lock file found, locking environment now")
            lock(build_system=build_system, platforms=get_conda_platforms())
        log.info(f"Syncing environment {Config.get().venv_name}")
        do_conda_install(
            conda=Config.get().conda_path,
            name=Config.get().venv_name,
            prefix=None,
            file=str(Config.get().platform_conda_lock),
        )
    else:
        raise NotImplementedError()


@app.command()
def shell(build_system: BuildSystem = typer.Option(get_default_build_system)):
    environ["PYSENV_ACTIVE"] = "1"
    environ["PATH"] = f"{Config.get().conda_path.parent}:{environ.get('PATH')}"
    if build_system == BuildSystem.POETRY:
        with cd(Config.get().config_path.parent):
            PysenvShell.get().activate(command="poetry shell")
    elif build_system == BuildSystem.CONDA:
        PysenvShell.get().activate(command=f"conda activate {Config.get().venv_name}")
    else:
        raise NotImplementedError()
    environ["PATH"] = ":".join(environ.get("PATH").split(":")[1:])
    environ.pop("PYSENV_ACTIVE")


@app.command()
def lock(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    platforms: List[str] = typer.Option(
        get_conda_platforms,
        case_sensitive=False,
        help="conda platforms, for example osx-64 or linux-64",
    ),
):
    platforms = platforms
    if build_system == BuildSystem.POETRY:
        with cd(Config.get().config_path.parent):
            subprocess.check_call([Config.get().poetry_path, "lock"])
    elif build_system == BuildSystem.CONDA:
        log.info("Building conda env from pyproject.toml")
        env_dict = pyproject_to_conda_venv_dict()
        with NamedTemporaryFile(mode="w+") as f:
            Config.get().pysenv.venv.conda_lock_dir.mkdir(exist_ok=True, parents=True)
            with cd(Config.get().pysenv.venv.conda_lock_dir):
                yaml.safe_dump(env_dict, f)
                run_lock(
                    [Path(f.name)],
                    conda_exe=Config.get().conda_path,
                    platforms=platforms,
                )
        log.info("lock files updated, sync environment running `pysenv env sync`")
    else:
        raise NotImplementedError()
