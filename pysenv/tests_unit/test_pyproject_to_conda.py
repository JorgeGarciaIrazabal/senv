from .conftest import STATIC_PATH
from ..dev_env.pyproject_to_conda import pyproject_to_recipe_dict


def test_pyproject_to_conda_creates_recipe_with_deps(mocker):
    normalize = mocker.patch(
        "conda_lock.src_parser.pyproject_toml.normalize_pypi_name"
    )
    normalize.side_effect = lambda name: name
    recipe = pyproject_to_recipe_dict(STATIC_PATH / "simple_pyproject.toml")
    deps = recipe["requirements"]["run"]
    assert len(deps) == 7
