from pytest import fixture, mark

from senv.main import app
from senv.tests.conftest import STATIC_PATH
from senv.utils import cd


@fixture()
def temp_small_conda_pyproject(build_temp_pyproject):
    return build_temp_pyproject(STATIC_PATH / "small_conda_pyproject.toml")


@fixture()
def temp_simple_pyproject(build_temp_pyproject):
    return build_temp_pyproject(STATIC_PATH / "simple_pyproject.toml")


def test_build_conda_installs_conda_build_if_necessary(
    temp_small_conda_pyproject, cli_runner
):
    with cd(temp_small_conda_pyproject.parent):
        result = cli_runner.invoke(
            app, ["-f", str(temp_small_conda_pyproject), "package", "build"], input="y"
        )
    assert result.exit_code == 0, str(result.exception)


def test_build_simple_pyproject_with_conda_even_with_poetry_build_system_in_pyproject(
    temp_simple_pyproject, cli_runner
):
    with cd(temp_simple_pyproject.parent):
        result = cli_runner.invoke(
            app,
            ["-f", str(temp_simple_pyproject), "package", "build"],
            input="y",
            catch_exceptions=False,
        )
    assert result.exit_code == 0, result.exception


def test_publish_conda_raises_exception_if_repository_url_is_null(
    temp_small_conda_pyproject, cli_runner
):
    with cd(temp_small_conda_pyproject.parent):
        result = cli_runner.invoke(
            app,
            ["-f", str(temp_small_conda_pyproject), "package", "publish"],
            input="y",
        )
    assert result.exit_code == 1
    assert isinstance(result.exception, NotImplementedError)
