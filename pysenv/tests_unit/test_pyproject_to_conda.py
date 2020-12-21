from .conftest import STATIC_PATH
from ..dev_env.pyproject_to_conda import (
    pyproject_to_conda_dev_env_dict,
    pyproject_to_recipe_dict,
)

SIMPLE_PYPROJECT_TOML = STATIC_PATH / "simple_pyproject.toml"
PYSENV_OVERRIDE_PYPROJECT_TOML = STATIC_PATH / "pysenv_override_pyproject.toml"


def test_pyproject_to_conda_creates_recipe_with_deps():
    recipe = pyproject_to_recipe_dict(SIMPLE_PYPROJECT_TOML)
    deps = recipe["requirements"]["run"]
    dep_names = [d.split(" ")[0] for d in deps]
    # it should ignore the dev-environments
    assert len(deps) == 7
    assert "python" in dep_names
    assert "ensureconda" in dep_names
    assert "condax" in dep_names
    assert "click" in dep_names
    assert "tomlkit" in dep_names
    assert "appdirs" in dep_names
    assert "conda-lock" in dep_names


def test_pyproject_to_conda_creates_recipe_right_params():
    recipe = pyproject_to_recipe_dict(SIMPLE_PYPROJECT_TOML)
    # it should ignore the dev-environments
    assert recipe["package"]["name"] == "test_name"
    assert recipe["package"]["version"] == "0.1.0"
    assert "python" in recipe["requirements"]["host"][0]
    assert "3.7.0" in recipe["requirements"]["host"][0]


def test_pyproject_to_conda_dev_env_dict_generates_env_with_dev_deps():
    env_dict = pyproject_to_conda_dev_env_dict(SIMPLE_PYPROJECT_TOML)
    dep_names = [d.split(" ")[0] for d in env_dict["dependencies"]]

    assert len(env_dict["dependencies"]) == 9
    # it should not ignore the dev-environments
    assert "python" in dep_names
    assert "ensureconda" in dep_names
    assert "appdirs" in dep_names
    assert "pyinstaller" in dep_names
    assert "pytest" in dep_names


def test_pyproject_to_conda_dev_env_dict_has_no_channel_and_basic_name():
    env_dict = pyproject_to_conda_dev_env_dict(SIMPLE_PYPROJECT_TOML)
    assert len(env_dict["channels"]) == 0
    assert env_dict["name"] == "test_name"


def test_pyproject_to_conda_dev_env_dict_pysenv_overrides_values():
    env_dict = pyproject_to_conda_dev_env_dict(PYSENV_OVERRIDE_PYPROJECT_TOML)
    assert len(env_dict["channels"]) == 2
    assert env_dict["name"] == "overridden_name"
