import os
import subprocess
from enum import Enum, auto
from pathlib import Path
from sys import platform
from tempfile import NamedTemporaryFile

import click
import toml
import yaml
from click import BadParameter
from conda_lock.conda_lock import DEFAULT_PLATFORMS, do_conda_install, run_lock
from ensureconda import ensureconda

from .pyproject_to_conda import pyproject_to_conda_dev_env_dict
from ..errors import PysenvNotSupportedPlatform
from ..log import log


class BuildSystem(Enum):
    CONDA = auto()
    POETRY = auto()


@click.group()
@click.option("--pyproject-file", "-f", type=click.Path(), default="pyproject.toml")
@click.pass_context
def cli(ctx, pyproject_file):
    ctx.ensure_object(dict)
    ctx.obj["conda_path"] = ensureconda(micromamba=False, mamba=False)
    pyproject_path: Path = Path(ctx.params["pyproject_file"])
    ctx.obj["pyproject_path"] = pyproject_path
    if not pyproject_path.exists():
        # log.error(f"{pyproject_path.absolute()} Not found")
        raise BadParameter(f"{pyproject_path.absolute()} Not found")

    ctx.obj["pyproject"] = toml.load(ctx.params["pyproject_file"])


@cli.group("env")
@click.pass_context
def env(ctx):
    pass


@env.command()
@click.option(
    "--conda", "-c", "build_system", flag_value=BuildSystem.CONDA, default=True
)
@click.option("--poetry", "-p", "build_system", flag_value=BuildSystem.POETRY)
@click.pass_context
def install(ctx, build_system):
    click.echo(f"Installing environment {build_system}")


@env.command()
@click.option(
    "--conda", "-c", "build_system", flag_value=BuildSystem.CONDA, default=True
)
@click.option("--poetry", "-p", "build_system", flag_value=BuildSystem.POETRY)
@click.pass_context
def sync(ctx, build_system):
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


@cli.command()
@click.pass_context
def shell(ctx):
    name = ctx.obj["pyproject"]["tool"]["pysenv"]["env-name"]
    env = os.environ.copy()
    subprocess.run("/home/jirazabal/code/pysenv/activate_conda.sh", shell=False, env=env)

@env.command()
@click.option(
    "--conda", "-c", "build_system", flag_value=BuildSystem.CONDA, default=True
)
@click.option("--poetry", "-p", "build_system", flag_value=BuildSystem.POETRY)
@click.option(
    "--platform",
    "platforms",
    type=click.Choice(DEFAULT_PLATFORMS, case_sensitive=False),
    multiple=True,
    default=DEFAULT_PLATFORMS,
)
@click.pass_context
def lock(
    ctx,
    build_system,
    platforms,
):
    if build_system == BuildSystem.POETRY:
        raise NotImplementedError()
    elif build_system == BuildSystem.CONDA:
        log.info("Building conda env from pyproject.toml")
        env_dict = pyproject_to_conda_dev_env_dict(ctx.obj["pyproject_path"])
        with NamedTemporaryFile(mode="w+") as f:
            yaml.safe_dump(env_dict, f)
            run_lock([Path(f.name)], conda_exe=None, platforms=platforms)
        log.info("lock files updated, sync environment running `pysenv env sync`")
    else:
        raise NotImplementedError()


if __name__ == "__main__":
    cli()
