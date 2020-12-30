from pathlib import Path

import typer

from pysenv.config import Config
from pysenv.dev_env import env

app = typer.Typer()
app.add_typer(env.app, name="env")


@app.callback()
def users_callback(
    pyproject_file: Path = typer.Option(
        Path(".") / "pyproject.toml", "-f", "--pyproject-file", exists=True
    )
):
    typer.echo(f"{pyproject_file}")
    Config.read_toml(pyproject_file)

    # ctx.ensure_object(dict)
    # ctx.obj["conda_path"] = ensureconda(micromamba=False, mamba=False)
    # pyproject_path: Path = Path(ctx.params["pyproject_file"])
    # ctx.obj["pyproject_path"] = pyproject_path
    # if not pyproject_path.exists():
    #     # log.error(f"{pyproject_path.absolute()} Not found")
    #     raise BadParameter(f"{pyproject_path.absolute()} Not found")
    #
    # ctx.obj["pyproject"] = toml.load(ctx.params["pyproject_file"])


if __name__ == "__main__":
    app()
