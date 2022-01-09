from enum import Enum
from pathlib import Path

import typer
from poetry.core.pyproject import PyProjectTOML
from pydantic import ValidationError

from senv.log import log
from senv.pyproject import PyProject


class AllowedConfigKeys(str, Enum):
    BUILD_SYSTEM = "build-system"
    CONDA_CHANNELS = "conda-channels"
    CONDA_PATH = "conda-path"
    POETRY_PATH = "poetry-path"
    CONDA_PUBLISH_CHANNEL = "package.conda-publish-channel"
    POETRY_PUBLISH_REPOSITORY = "poetry-publish-repository"
    CONDA_PLATFORMS = "env.conda-lock-platforms"
    CONDA_ENV_LOCK_PATH = "env.conda-lock-path"
    ENV_BUILD_SYSTEM = "env.build-system"
    CONDA_PACKAGE_LOCK_PATH = "package.conda-lock-path"


CONFIG_KEYS_MULTIPLE = {
    AllowedConfigKeys.CONDA_CHANNELS,
    AllowedConfigKeys.CONDA_PLATFORMS,
}

app = typer.Typer(add_completion=False)


def _validate_toml(toml):
    try:
        c = PyProject(**toml)
        c._config_path = PyProject.get().config_path
        c.validate_fields()
    except ValidationError as e:
        log.error(str(e))
        raise typer.Abort()


def set_config_value_to_pyproject(path: Path, key: str, value: str):
    pyproject = PyProjectTOML(path)
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

    _validate_toml(dict(toml.items()))
    pyproject.file.write(toml)


@app.command(name="set")
def set_new_setting_value(
    key: AllowedConfigKeys = typer.Argument(...),
    value: str = typer.Argument(
        None,
        help="Value of the setting. For multi value setting like the conda-platforms,"
        " separate them with a comma ','",
    ),
):
    set_config_value_to_pyproject(PyProject.get().config_path, key, value)


def remove_config_value_from_pyproject(path: Path, key: str):
    pyproject = PyProjectTOML(path)
    toml = pyproject.file.read()

    sub_toml = toml
    for k in key.split(".")[:-1]:
        if k not in sub_toml:
            typer.Abort()
        sub_toml = sub_toml[k]

    last_key = key.split(".")[-1]
    del sub_toml[last_key]

    _validate_toml(dict(toml.items()))
    pyproject.file.write(toml)


@app.command(name="remove")
def remove_config_value(key: AllowedConfigKeys = typer.Argument(...)):
    remove_config_value_from_pyproject(PyProject.get().config_path, f"tool.senv.{key}")
