from pathlib import Path
from sys import platform
from tempfile import NamedTemporaryFile
from typing import List

import click
import typer
import yaml
from conda_lock.conda_lock import DEFAULT_PLATFORMS, do_conda_install, run_lock

from pysenv.config.config_manager import BuildSystem
from pysenv.dev_env.pyproject_to_conda import pyproject_to_conda_venv_dict
from pysenv.errors import PysenvNotSupportedPlatform
from pysenv.log import log

app = typer.Typer()


def get_default_build_system():
    return config_reader.build_system()


@app.command()
def install(build_system: BuildSystem = typer.Option(get_default_build_system)):
    click.echo(f"Installing environment {build_system}")


@app.command()
def sync(build_system: BuildSystem = typer.Option(get_default_build_system)):
    if build_system == BuildSystem.POETRY:
        raise NotImplementedError()
    elif build_system == BuildSystem.CONDA:
        if platform == "linux" or platform == "linux2":
            plat = "linux-64"
        elif platform == "darwin":
            plat = "osx-64"
        elif platform == "win32":
            plat = "win-64"
        else:
            raise PysenvNotSupportedPlatform(f"Platform {platform} not supported")

        lock_path = ctx.obj["pyproject_path"].parent / f"conda-{plat}.lock"
        log.info(
            f"Syncing environment {ctx.obj['pyproject']['tool']['pysenv']['env-name']}"
        )
        do_conda_install(
            conda=ctx.obj["conda_path"],
            name=ctx.obj["pyproject"]["tool"]["pysenv"]["env-name"],
            prefix=None,
            file=str(lock_path),
        )
    else:
        raise NotImplementedError()


# @cli.command()
# @click.pass_context
# def shell(ctx):
#     name = ctx.obj["pyproject"]["tool"]["pysenv"]["env-name"]
#     env = os.environ.copy()
#     subprocess.run("/home/jirazabal/code/pysenv/activate_conda.sh", shell=False, env=env)


@app.command()
def lock(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    platforms: List[str] = typer.Option(
        DEFAULT_PLATFORMS,
        case_sensitive=False,
        help=f"conda platforms, for example osx-64 or linux-64",
    ),
):
    if build_system == BuildSystem.POETRY:
        raise NotImplementedError()
    elif build_system == BuildSystem.CONDA:
        log.info("Building conda env from pyproject.toml")
        env_dict = pyproject_to_conda_venv_dict(ctx.obj["pyproject_path"])
        with NamedTemporaryFile(mode="w+") as f:
            yaml.safe_dump(env_dict, f)
            run_lock([Path(f.name)], conda_exe=None, platforms=platforms)
        log.info("lock files updated, sync environment running `pysenv env sync`")
    else:
        raise NotImplementedError()


if __name__ == "__main__":
    cli()
