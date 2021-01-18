from pathlib import Path

from pytest import fixture
from typer.testing import CliRunner

from senv.conda_publish import LockFileMetaData
from senv.errors import SenvNotAllRequiredLockFiles
from senv.main import app
from senv.pyproject import PyProject
from senv.tests.conftest import STATIC_PATH
from senv.utils import cd


@fixture()
def temp_small_conda_pyproject(build_temp_pyproject):
    return build_temp_pyproject(STATIC_PATH / "small_conda_pyproject.toml")


@fixture()
def temp_appdirs_pyproject(build_temp_pyproject):
    return build_temp_pyproject(STATIC_PATH / "appdirs_pyproject.toml")


@fixture()
def temp_simple_pyproject(build_temp_pyproject):
    return build_temp_pyproject(STATIC_PATH / "simple_pyproject.toml")


@fixture()
def appdirs_venv_lock_path(temp_appdirs_pyproject) -> Path:
    with cd(temp_appdirs_pyproject.parent):
        # venv lock first to get the venv locks that we will use to tests our code
        result = CliRunner().invoke(
            app,
            [
                "-f",
                str(temp_appdirs_pyproject),
                "venv",
                "lock",
                "--platforms",
                "linux-64",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        venv_lock_path = PyProject.get().senv.venv.venv_lock_dir / "conda-linux-64.lock"
        yield venv_lock_path


def test_build_conda_installs_conda_build_if_necessary(
    temp_small_conda_pyproject, cli_runner
):
    with cd(temp_small_conda_pyproject.parent):
        result = cli_runner.invoke(
            app,
            ["-f", str(temp_small_conda_pyproject), "package", "build"],
            input="y",
            catch_exceptions=False,
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


def test_lock_appdirs_simple_does_not_include_fake_dependencies(
    temp_appdirs_pyproject, cli_runner
):
    with cd(temp_appdirs_pyproject.parent):
        result = cli_runner.invoke(
            app,
            [
                "-f",
                str(temp_appdirs_pyproject),
                "package",
                "lock",
                "--platforms",
                "linux-64",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        lock_path = PyProject.get().senv.package_lock_dir / "conda-linux-64.lock"
        assert lock_path.exists()
        assert "click" not in lock_path.read_text()


def test_lock_appdirs_simple_includes_metadata(temp_appdirs_pyproject, cli_runner):
    with cd(temp_appdirs_pyproject.parent):
        cli_runner.invoke(
            app,
            [
                "-f",
                str(temp_appdirs_pyproject),
                "package",
                "lock",
                "--platforms",
                "osx-64",
            ],
            catch_exceptions=False,
        )
        lock_path = PyProject.get().senv.package_lock_dir / "conda-osx-64.lock"
        metadata = LockFileMetaData.from_lock_path(lock_path)
        assert metadata.package_name == "appdirs"
        assert metadata.entry_points == []


def test_lock_based_on_tested_includes_pinned_dependencies(
    temp_appdirs_pyproject, cli_runner, appdirs_venv_lock_path
):
    with cd(temp_appdirs_pyproject.parent):
        click_line = next(
            l for l in appdirs_venv_lock_path.read_text().splitlines() if "click" in l
        )

        result = cli_runner.invoke(
            app,
            [
                "-f",
                str(temp_appdirs_pyproject),
                "package",
                "lock",
                "--platforms",
                "linux-64",
                "--based-on-tested-lock-files-template",
                str(appdirs_venv_lock_path.resolve()).replace("linux-64", "{platform}"),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        lock_path = PyProject.get().senv.package_lock_dir / "conda-linux-64.lock"

        assert lock_path.exists()
        assert click_line in lock_path.read_text()


def test_lock_throws_if_not_all_lock_files_exist(temp_appdirs_pyproject, cli_runner):
    with cd(temp_appdirs_pyproject.parent):
        fake_linux_lock_path = Path("my_lock_file_linux-64.lock")
        fake_linux_lock_path.write_text("dummy text")
        result = cli_runner.invoke(
            app,
            [
                "-f",
                str(temp_appdirs_pyproject),
                "package",
                "lock",
                "--platforms",
                "osx-64",
                "--platforms",
                "win-64",
                "--platforms",
                "linux-64",
                "--based-on-tested-lock-files-template",
                str(fake_linux_lock_path.resolve()).replace("linux-64", "{platform}"),
            ],
        )
        assert result.exit_code != 0
        assert isinstance(result.exception, SenvNotAllRequiredLockFiles)
        assert set(result.exception.missing_lock_files) == {
            Path(fake_linux_lock_path.parent, "my_lock_file_osx-64.lock").resolve(),
            Path(fake_linux_lock_path.parent, "my_lock_file_win-64.lock").resolve(),
        }
