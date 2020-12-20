from enum import Enum, auto
from pathlib import Path

import click

from click import BadParameter


class BuildSystem(Enum):
    CONDA = auto()
    POETRY = auto()


@click.group()
@click.option("--pyproject-path", "-f", type=click.Path(), default="pyproject.toml")
@click.pass_context
def cli(ctx, pyproject_path):
    print(pyproject_path)
    ctx.ensure_object(dict)
    pyproject_path: Path = Path(ctx.params["pyproject_path"])
    ctx.obj["pyproject_path"] = pyproject_path
    if not pyproject_path.exists():
        # log.error(f"{pyproject_path.absolute()} Not found")
        raise BadParameter(f"{pyproject_path.absolute()} Not found")


@cli.group("env")
@click.pass_context
def env(ctx):
    print("env")
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
@click.option("--conda/--no-conda", "-c", type=bool, default=True)
def configure(conda):
    click.echo(f"Installing environment {conda}")


if __name__ == "__main__":
    cli()
