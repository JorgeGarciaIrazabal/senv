from shutil import copyfile

import pytest

from pysenv.config import BuildSystem, Config
from pysenv.main import app
from pysenv.tests.conftest import STATIC_PATH


@pytest.fixture()
def temp_pyproject(tmp_path):
    simple_pyproject = STATIC_PATH / "simple_pyproject.toml"
    temp_path = tmp_path / "simple_pyproject.toml"
    copyfile(simple_pyproject, temp_path)
    return temp_path


def test_set_config_add_value_to_pyproject(temp_pyproject, cli_runner):
    cli_runner.invoke(
        app,
        [
            "-f",
            str(temp_pyproject),
            "config",
            "set",
            "venv.conda-lock-platforms",
            "linux",
        ],
    )

    Config.read_toml(temp_pyproject)
    assert Config.get().pysenv.venv.conda_lock_platforms == {"linux"}


def test_set_config_with_wrong_value_does_not_change_pyproject(
    temp_pyproject, cli_runner
):
    original_config = Config.read_toml(temp_pyproject).dict()
    cli_runner.invoke(
        app,
        [
            "-f",
            str(temp_pyproject),
            "config",
            "set",
            "conda-path",
            "none_existing_path",
        ],
        catch_exceptions=False,
    )

    new_config = Config.read_toml(temp_pyproject).dict()
    assert new_config == original_config


def test_remove_config_key_removes_it_from_file(temp_pyproject, cli_runner):
    cli_runner.invoke(
        app,
        ["-f", str(temp_pyproject), "config", "set", "venv.build-system", "poetry"],
    )

    cli_runner.invoke(
        app,
        ["-f", str(temp_pyproject), "config", "remove", "venv.build-system"],
    )

    assert (
        Config.read_toml(temp_pyproject).pysenv.venv.build_system == BuildSystem.CONDA
    )
