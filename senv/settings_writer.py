from enum import Enum

import typer
from poetry.core.pyproject import PyProjectTOML
from pydantic import ValidationError

from senv.commands.config import Config
from senv.log import log


class AllowedConfigKeys(str, Enum):
    BUILD_SYSTEM = "build-system"
    CONDA_CHANNELS = "conda-channels"
    CONDA_PATH = "conda-path"
    POETRY_PATH = "poetry-path"
    CONDA_PUBLISH_CHANNEL = "conda-publish-channel"
    POETRY_PUBLISH_REPOSITORY = "poetry-publish-repository"
    CONDA_PLATFORMS = "venv.conda-lock-platforms"
    CONDA_LOCK_DIRECTORY = "venv.conda-lock-dir"
    VENV_BUILD_SYSTEM = "venv.build-system"


CONFIG_KEYS_MULTIPLE = {
    AllowedConfigKeys.CONDA_CHANNELS,
    AllowedConfigKeys.CONDA_PLATFORMS,
}


app = typer.Typer()


def _validate_toml(toml):
    try:
        Config(**toml).validate_fields()
    except ValidationError as e:
        log.error(str(e))
        raise typer.Abort()


@app.command(name="set")
def set_new_setting_value(
    key: AllowedConfigKeys = typer.Argument(...),
    value: str = typer.Argument(
        None,
        help="Value of the setting. For multi value setting like the conda-platforms,"
        " separate them with a comma ','",
    ),
):
    pyproject = PyProjectTOML(Config.get().config_path)
    toml = pyproject.file.read()

    sub_dict = toml
    for k in f"tool.senv.{key}".split(".")[:-1]:
        sub_dict[k] = sub_dict.get(k, default={})
        sub_dict = sub_dict[k]

    last_key = key.split(".")[-1]

    if key in CONFIG_KEYS_MULTIPLE:
        sub_dict[last_key] = [v.strip() for v in value.split(",")]
    else:
        sub_dict[last_key] = value

    _validate_toml(toml)
    pyproject.file.write(toml)


@app.command(name="remove")
def remove_config_value(key: AllowedConfigKeys = typer.Argument(...)):
    pyproject = PyProjectTOML(Config.get().config_path)
    toml = pyproject.file.read()

    sub_toml = toml
    for k in f"tool.senv.{key}".split(".")[:-1]:
        if k not in sub_toml:
            typer.Abort()
        sub_toml = sub_toml[k]

    last_key = key.split(".")[-1]
    del sub_toml[last_key]

    _validate_toml(toml)
    pyproject.file.write(toml)
