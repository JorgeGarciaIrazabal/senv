import os
from pathlib import Path
from typing import Any, Dict

import pytest
import toml

from senv.errors import SenvBadConfiguration
from senv.pyproject import BuildSystem, PyProject
from senv.utils import cd


def test_config_defaults_get_populated():
    config_dict = {
        "tool": {
            "senv": {"venv": {"name": "my_virtual_environment"}, "name": "test_name"}
        }
    }

    config = PyProject(**config_dict)
    assert config.senv.venv.name == "my_virtual_environment"
    assert isinstance(config.senv.venv.build_system, BuildSystem)
    assert isinstance(config.senv.venv.conda_lock_platforms, set)


def test_config_build_system_has_to_be_enum():
    config_dict = {
        "tool": {"senv": {"name": "test_name", "venv": {"build-system": "poetry"}}}
    }
    config = PyProject(**config_dict)
    assert config.senv.venv.build_system == BuildSystem.POETRY

    config_dict["tool"]["senv"]["venv"]["build-system"] = "no_build_system"
    with pytest.raises(ValueError):
        PyProject(**config_dict)


@pytest.mark.parametrize("key", ["conda-path", "poetry-path"])
def test_config_conda_and_poetry_path_have_to_exists(key):
    config_dict = {
        "tool": {
            "senv": {
                key: str(Path("/no/real/path")),
            }
        }
    }
    try:
        PyProject(**config_dict)
        pytest.fail("config should raise exception as paths do not exists")
    except ValueError as e:
        assert "not found" in str(e).lower()
        assert "not executable" not in str(e).lower()


@pytest.mark.parametrize("key", ["conda-path", "poetry-path"])
def test_config_conda_and_poetry_path_have_to_be_executable(key):
    config_dict = {
        "tool": {
            "senv": {
                key: str(Path(__file__)),
            }
        }
    }
    try:
        PyProject(**config_dict)
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
            "senv": {
                "name": "test_name",
                "conda-path": str(my_file),
            }
        }
    }
    config = PyProject(**config_dict)
    assert config.conda_path == my_file


def test_senv_overrides_poetry():
    config_dict = {
        "tool": {
            "poetry": {
                "version": "poetry1",
                "description": "poetry2",
                "name": "poetry3",
            },
            "senv": {
                "version": "senv1",
                "description": "senv2",
                "name": "senv3",
            },
        }
    }
    config = PyProject(**config_dict)
    assert config.version == "senv1"
    assert config.senv.description == "senv2"
    assert config.package_name == "senv3"

    # without senv, it should use the poetry information
    del config_dict["tool"]["senv"]
    config = PyProject(**config_dict)
    assert config.version == "poetry1"
    assert config.senv.description == "poetry2"
    assert config.package_name == "poetry3"


def test_conda_build_dir_can_not_be_in_project(tmp_path):
    tmp_toml = tmp_path / "tmp_toml"
    config_dict = {
        "tool": {
            "senv": {
                "name": "senv3",
                "conda-build-path": "./dist",
            },
        }
    }
    tmp_toml.write_text(toml.dumps(config_dict))

    with cd(tmp_path), pytest.raises(SenvBadConfiguration):
        PyProject.read_toml(tmp_toml)


def test_dependencies_are_not_combined(tmp_path):
    config_dict = {
        "tool": {
            "poetry": {
                "name": "senv3",
                "dependencies": {"package1": "*", "package2": "1"},
            },
            "senv": {
                "dependencies": {"package1": "*", "package3": "2"},
            },
        }
    }
    config = PyProject(**config_dict)
    assert config.senv.dependencies == {"package1": "*", "package3": "2"}


def test_values_in_poetry_gets_populated_to_senv():
    config_dict = {
        "tool": {
            "poetry": {
                "name": "senv3",
                "dependencies": {"package1": "*", "package2": "1"},
                "version": "poetry1",
                "description": "poetry2",
            },
        }
    }
    config = PyProject(**config_dict)
    assert config.senv.dependencies == {"package1": "*", "package2": "1"}
    assert config.senv.version == "poetry1"
    assert config.senv.description == "poetry2"


def test_venv_name_default_to_package_name():
    config_dict: Dict[str, Any] = {
        "tool": {
            "senv": {
                "name": "p_name",
            },
        }
    }
    config = PyProject(**config_dict)
    assert config.venv.name == "p_name"
    config_dict["tool"]["senv"]["venv"] = {"name": "venv_name"}
    config2 = PyProject(**config_dict)
    assert config2.venv.name == "venv_name"
