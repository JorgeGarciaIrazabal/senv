import os
from pathlib import Path

import pytest

from pysenv.config import BuildSystem, Config


def test_config_defaults_get_populated():
    config_dict = {"tool": {"pysenv": {"venv": {"name": "my_virtual_environment"}}}}

    config = Config(**config_dict)
    assert config.pysenv.venv.name == "my_virtual_environment"
    assert isinstance(config.pysenv.venv.build_system, BuildSystem)
    assert isinstance(config.pysenv.venv.conda_platforms, set)


def test_config_build_system_has_to_be_enum():
    config_dict = {"tool": {"pysenv": {"venv": {"build-system": "poetry"}}}}
    config = Config(**config_dict)
    assert config.pysenv.venv.build_system == BuildSystem.POETRY

    config_dict["tool"]["pysenv"]["venv"]["build-system"] = "no_build_system"
    with pytest.raises(ValueError):
        Config(**config_dict)


@pytest.mark.parametrize("key", ["conda-path", "poetry-path"])
def test_config_conda_and_poetry_path_have_to_exists(key):
    config_dict = {
        "tool": {
            "pysenv": {
                key: str(Path("/no/real/path")),
            }
        }
    }
    try:
        Config(**config_dict)
        pytest.fail("config should raise exception as paths do not exists")
    except ValueError as e:
        assert "not found" in str(e).lower()
        assert "not executable" not in str(e).lower()


@pytest.mark.parametrize("key", ["conda-path", "poetry-path"])
def test_config_conda_and_poetry_path_have_to_be_executable(key):
    config_dict = {
        "tool": {
            "pysenv": {
                key: str(Path(__file__)),
            }
        }
    }
    try:
        Config(**config_dict)
        pytest.fail("config should raise exception as path is not executable")
    except ValueError as e:
        assert "not executable" in str(e).lower()
        assert "not found" not in str(e).lower()


def test_config_conda_and_poetry_path_do_not_raises_if_it_exists_and_is_executable(
    tmp_path,
):
    my_file = tmp_path / "executable.sh"
    my_file.write_text("echo test")
    os.chmod(my_file, 0o777)
    config_dict = {
        "tool": {
            "pysenv": {
                "conda-path": str(my_file),
            }
        }
    }
    config = Config(**config_dict)
    assert config.conda_path == my_file


def test_pysenv_overrides_poetry():
    config_dict = {
        "tool": {
            "poetry": {
                "version": "poetry1",
                "description": "poetry2",
                "name": "poetry3",
            },
            "pysenv": {
                "version": "pysenv1",
                "description": "pysenv2",
                "name": "pysenv3",
            },
        }
    }
    config = Config(**config_dict)
    assert config.version == "pysenv1"
    assert config.description == "pysenv2"
    assert config.package_name == "pysenv3"

    # without pysenv, it should use the poetry information
    del config_dict["tool"]["pysenv"]
    config = Config(**config_dict)
    assert config.version == "poetry1"
    assert config.description == "poetry2"
    assert config.package_name == "poetry3"
