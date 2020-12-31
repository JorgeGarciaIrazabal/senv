from pathlib import Path

import typer

from pysenv.config import Config
from pysenv.settings_writer import settings_writer
from pysenv.venv import venv

app = typer.Typer()
app.add_typer(venv.app, name="venv")
app.add_typer(settings_writer.app, name="config")


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
