from shutil import copyfile

from pytest import fixture

from senv.main import app
from senv.tests.conftest import STATIC_PATH
from senv.utils import cd


@fixture()
def temp_pyproject(tmp_path):
    temp_path = tmp_path / "pyproject.toml"
    copyfile(STATIC_PATH / "small_conda_pyproject.toml", temp_path)
    return temp_path


def test_build_conda_installs_conda_build_if_necessary(temp_pyproject, cli_runner):
    with cd(temp_pyproject.parent):
        result = cli_runner.invoke(
            app, ["-f", str(temp_pyproject), "package", "build"], input="y"
        )
    assert result.exit_code == 0, str(result.exception)


def test_publish_conda_raises_exception_if_repository_url_is_null(
    temp_pyproject, cli_runner
):
    with cd(temp_pyproject.parent):
        result = cli_runner.invoke(
            app, ["-f", str(temp_pyproject), "package", "publish"], input="y"
        )
    assert result.exit_code == 1
    assert isinstance(result.exception, NotImplementedError)
