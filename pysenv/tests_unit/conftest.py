from pathlib import Path
from pytest import fixture

TESTS_PATH = Path(__file__).parent.resolve()
STATIC_PATH = TESTS_PATH / "static"


@fixture(autouse=True)
def mock_normalize_pypi_name(mocker):
    normalize = mocker.patch("conda_lock.src_parser.pyproject_toml.normalize_pypi_name")
    normalize.side_effect = lambda name: name
