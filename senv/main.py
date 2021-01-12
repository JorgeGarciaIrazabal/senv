from pathlib import Path

import typer

from senv.commands import package, settings_writer, venv
from senv.config import Config

app = typer.Typer()
app.add_typer(venv.app, name="venv")
app.add_typer(settings_writer.app, name="config")
app.add_typer(package.app, name="package")


@app.callback()
def users_callback(
    pyproject_file: Path = typer.Option(
        Path(".") / "pyproject.toml", "-f", "--pyproject-file", exists=True
    )
):
    typer.echo(f"{pyproject_file}")
    Config.read_toml(pyproject_file)


if __name__ == "__main__":
    app()
