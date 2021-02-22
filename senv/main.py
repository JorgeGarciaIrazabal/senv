from os import chdir
from pathlib import Path
from textwrap import dedent

import click
import typer
from ensureconda import ensureconda

from senv.commands import package, settings_writer, venv
from senv.pyproject import BuildSystem, PyProject


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


def pyproject_callback(
    pyproject_file: Path = typer.Option(
        Path(".") / "pyproject.toml", "-f", "--pyproject-file", exists=True
    )
):
    PyProject.read_toml(pyproject_file)
    chdir(PyProject.get().config_path.parent)


app = typer.Typer(cls=AliasedGroup)
app.add_typer(
    venv.app,
    name="venv",
    no_args_is_help=True,
    help="Create and manage you virtual environment",
    callback=pyproject_callback,
)
app.add_typer(
    settings_writer.app,
    name="config",
    no_args_is_help=True,
    help="{alias 'c'} Add or remove configuration to pyproject.yaml",
    callback=pyproject_callback,
)
app.add_typer(
    package.app,
    name="package",
    no_args_is_help=True,
    help="{alias 'p'} build or publish your project",
    callback=pyproject_callback,
)


def assert_file_does_not_exists(p: Path):
    if p.exists():
        raise typer.Exit(
            "pyproject.toml already exists on this project. "
            "You can manually add parameters to the senv project."
            "\nMore information in https://jorgegarciairazabal.github.io/senv/pyproject/"
        )


@app.command()
def init(
    pyproject_file: Path = typer.Option(
        Path(".") / "pyproject.toml",
        "-f",
        "--pyproject-file",
        callback=assert_file_does_not_exists,
    ),
    package_name: str = typer.Option(Path(".").resolve().name, prompt=True),
    default_build_system: BuildSystem = typer.Option(BuildSystem.CONDA, prompt=True),
):
    # no_pyproject_check()
    conda_exe = ensureconda(no_install=True, micromamba=False, mamba=False)
    if conda_exe is None:
        if typer.confirm("Conda not found, do you want to install it", default=True):
            typer.echo(
                f"Conda installed in {ensureconda(micromamba=False, mamba=False)}"
            )

    init_project_template = dedent(
        """
        [tool.senv]
        name = "{package_name}"
        version = "0.1.0"
        license = "Proprietary"
        build-system = "{build_system}"
        
        # description = "Describe your project"
        # authors = ["MyName <MyName@domanin.com>"]
        # readme = "README.md"
        # homepage = "https://homapage.com"

        
        [tool.senv.dependencies]
        # All the direct dependencies you package depend on
        python = ">3.7.0, <3.10.0"
        
        
        [tool.senv.dev-dependencies]
        # Dependencies needed for development (typical examples: pytest, mkdocs, etc.)
        # these dependencies will not be included when publishing the package
        """
    ).strip()
    pyproject_file.write_text(
        init_project_template.format(
            package_name=package_name, build_system=default_build_system.value
        )
    )


# renaming commands for documentation, this will not be used in production

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
