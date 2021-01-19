from os import chdir
from pathlib import Path

import click
import typer

from senv.commands import package, settings_writer, venv
from senv.pyproject import PyProject


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        aliases_map = {
            "c": "config",
            "p": "package",
        }
        aliased_cmd_name = aliases_map.get(cmd_name, cmd_name)
        rv = click.Group.get_command(self, ctx, aliased_cmd_name)
        if rv is not None:
            return rv
        return None


app = typer.Typer(cls=AliasedGroup)
app.add_typer(
    venv.app,
    name="venv",
    no_args_is_help=True,
    help="Create and manage you virtual environment",
)
app.add_typer(
    settings_writer.app,
    name="config",
    no_args_is_help=True,
    help="{alias 'c'} Add or remove configuration to pyproject.yaml",
)
app.add_typer(
    package.app,
    name="package",
    no_args_is_help=True,
    help="{alias 'p'} build or publish your project",
)


@app.callback()
def users_callback(
    pyproject_file: Path = typer.Option(
        Path(".") / "pyproject.toml", "-f", "--pyproject-file", exists=True
    )
):
    PyProject.read_toml(pyproject_file)
    chdir(PyProject.get().config_path.parent)


_venv_command = typer.main.get_command(venv.app)
_venv_command.name = "senv venv"
venv_command = _venv_command

_config_command = typer.main.get_command(settings_writer.app)
_config_command.name = "senv config"
config_command = _config_command


_package_command = typer.main.get_command(package.app)
_package_command.name = "senv package"
package_command = _package_command

if __name__ == "__main__":
    app()
