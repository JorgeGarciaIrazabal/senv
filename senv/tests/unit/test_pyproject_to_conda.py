from senv.config import Config
from senv.pyproject_to_conda import pyproject_to_conda_venv_dict, pyproject_to_meta
from senv.tests.conftest import STATIC_PATH

SIMPLE_PYPROJECT_TOML = STATIC_PATH / "simple_pyproject.toml"
SENV_OVERRIDE_PYPROJECT_TOML = STATIC_PATH / "senv_override_pyproject.toml"


def test_pyproject_to_conda_creates_recipe_with_deps():
    Config.read_toml(SIMPLE_PYPROJECT_TOML)
    recipe = pyproject_to_meta()
    deps = recipe.requirements.run
    dep_names = [d.split(" ")[0] for d in deps]
    # it should ignore the dev-environments
    assert len(deps) == 6
    assert "python" in dep_names
    assert "ensureconda" in dep_names
    assert "click" in dep_names
    assert "tomlkit" in dep_names
    assert "appdirs" in dep_names
    assert "conda-lock" in dep_names


def test_pyproject_to_conda_creates_recipe_right_params():
    Config.read_toml(SIMPLE_PYPROJECT_TOML)
    recipe = pyproject_to_meta()
    # it should ignore the dev-environments
    assert recipe.package.name == "test_name"
    assert recipe.package.version == "0.1.0"
    assert "python" in recipe.requirements.host[0]
    assert "3.7.0" in recipe.requirements.host[0]


def test_pyproject_to_conda_dev_env_dict_generates_env_with_dev_deps():
    Config.read_toml(SIMPLE_PYPROJECT_TOML)
    env_dict = pyproject_to_conda_venv_dict()
    dep_names = [d.split(" ")[0] for d in env_dict["dependencies"]]

    assert len(env_dict["dependencies"]) == 8
    # it should not ignore the dev-environments
    assert "python" in dep_names
    assert "ensureconda" in dep_names
    assert "appdirs" in dep_names
    assert "pyinstaller" in dep_names
    assert "pytest" in dep_names


def test_pyproject_to_conda_dev_env_dict_has_no_channel_and_basic_name():
    Config.read_toml(SIMPLE_PYPROJECT_TOML)
    env_dict = pyproject_to_conda_venv_dict()
    assert len(env_dict["channels"]) == 0
    assert env_dict["name"] == "test_name"


def test_pyproject_to_conda_dev_env_dict_senv_overrides_values():
    Config.read_toml(SENV_OVERRIDE_PYPROJECT_TOML)
    env_dict = pyproject_to_conda_venv_dict()
    assert len(env_dict["channels"]) == 2
    assert env_dict["name"] == "overridden_name"
