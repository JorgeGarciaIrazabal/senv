from pytest import fixture


@fixture(autouse=True)
def mock_normalize_pypi_name(mocker):
    normalize = mocker.patch("conda_lock.src_parser.pyproject_toml.normalize_pypi_name")
    normalize.side_effect = lambda name: name
