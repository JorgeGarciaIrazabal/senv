from shutil import copyfile

import pytest

from senv.main import app
from senv.pyproject import BuildSystem, PyProject
from senv.tests.conftest import STATIC_PATH


@pytest.fixture()
def temp_pyproject(tmp_path):
    simple_pyproject = STATIC_PATH / "simple_pyproject.toml"
    temp_path = tmp_path / "simple_pyproject.toml"
    copyfile(simple_pyproject, temp_path)
    return temp_path


def test_set_config_add_value_to_pyproject(temp_pyproject, cli_runner):
    result = cli_runner.invoke(
        app,
        [
            "config",
            "-f",
            str(temp_pyproject),
            "set",
            "venv.conda-lock-platforms",
            "linux-64",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    PyProject.read_toml(temp_pyproject)
    assert PyProject.get().senv.venv.conda_lock_platforms == {"linux-64"}


def test_set_config_with_wrong_value_does_not_change_pyproject(
    temp_pyproject, cli_runner
):
    original_config = PyProject.read_toml(temp_pyproject).dict()
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

    new_config = PyProject.read_toml(temp_pyproject).dict()
    assert new_config == original_config


def test_remove_config_key_removes_it_from_file(temp_pyproject, cli_runner):
    cli_runner.invoke(
        app,
        [
            "config",
            "set",
            "venv.build-system",
            "poetry",
            "-f",
            str(temp_pyproject),
        ],
    )

    cli_runner.invoke(
        app,
        [
            "config",
            "remove",
            "venv.build-system",
            "-f",
            str(temp_pyproject),
        ],
    )

    assert (
        PyProject.read_toml(temp_pyproject).senv.venv.build_system == BuildSystem.CONDA
    )
