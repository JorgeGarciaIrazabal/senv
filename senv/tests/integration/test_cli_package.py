from pathlib import Path

from pytest import fixture
from typer.testing import CliRunner

from senv.conda_publish import LockFileMetaData
from senv.errors import SenvNotAllPlatformsInBaseLockFile
from senv.main import app
from senv.pyproject import PyProject
from senv.senvx.models import CombinedCondaLock
from senv.tests.conftest import STATIC_PATH
from senv.utils import cd


@fixture()
def fake_combined_lock():
    return CombinedCondaLock(
        metadata=LockFileMetaData(), platform_tar_links={"linux-64": ["my_fake_url"]}
    )


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
def appdirs_env_lock_path(temp_appdirs_pyproject) -> Path:
    with cd(temp_appdirs_pyproject.parent):
        # env lock first to get the env locks that we will use to tests our code
        result = CliRunner().invoke(
            app,
            [
                "env",
                "-f",
                str(temp_appdirs_pyproject),
                "lock",
                "--platforms",
                "linux-64",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        yield PyProject.get().senv.env.conda_lock_path


def test_build_simple_pyproject_with_conda_even_with_poetry_build_system_in_pyproject(
    temp_simple_pyproject, cli_runner
):
    with cd(temp_simple_pyproject.parent):
        result = cli_runner.invoke(
            app,
            [
                "package",
                "-f",
                str(temp_simple_pyproject),
                "build",
            ],
            input="y",
            catch_exceptions=False,
        )
    assert result.exit_code == 0, result.exception


def test_publish_requires_username_and_password(temp_small_conda_pyproject, cli_runner):
    args = [
        "package",
        "-f",
        str(temp_small_conda_pyproject),
        "publish",
    ]
    with cd(temp_small_conda_pyproject.parent):
        result = cli_runner.invoke(
            app,
            args,
        )
        assert result.exit_code == 2, result.output
        result = cli_runner.invoke(
            app,
            args + ["-u", "username"],
        )
        assert result.exit_code == 2, result.output
        result = cli_runner.invoke(
            app,
            args + ["-p", "password"],
        )
        assert result.exit_code == 2, result.output


def test_lock_appdirs_simple_does_not_include_fake_dependencies(
    temp_appdirs_pyproject, cli_runner
):
    with cd(temp_appdirs_pyproject.parent):
        result = cli_runner.invoke(
            app,
            [
                "package",
                "-f",
                str(temp_appdirs_pyproject),
                "lock",
                "--platforms",
                "linux-64",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert PyProject.get().senv.package.conda_lock_path.exists()
        assert "click" not in PyProject.get().senv.package.conda_lock_path.read_text()


def test_lock_appdirs_simple_includes_metadata(temp_appdirs_pyproject, cli_runner):
    with cd(temp_appdirs_pyproject.parent):
        cli_runner.invoke(
            app,
            [
                "package",
                "-f",
                str(temp_appdirs_pyproject),
                "lock",
                "--platforms",
                "osx-64",
            ],
            catch_exceptions=False,
        )
        conda_lock = CombinedCondaLock.parse_file(
            PyProject.get().senv.package.conda_lock_path
        )
        assert conda_lock.metadata.package_name == "appdirs"
        assert conda_lock.metadata.entry_points == []


def test_lock_based_on_tested_includes_pinned_dependencies(
    temp_appdirs_pyproject, cli_runner, appdirs_env_lock_path
):
    with cd(temp_appdirs_pyproject.parent):
        click_line = next(
            l for l in appdirs_env_lock_path.read_text().splitlines() if "click" in l
        )

        result = cli_runner.invoke(
            app,
            [
                "package",
                "-f",
                str(temp_appdirs_pyproject),
                "lock",
                "--platforms",
                "linux-64",
                "--based-on-tested-lock-file",
                str(appdirs_env_lock_path.resolve()),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert PyProject.get().senv.package.conda_lock_path.exists()
        assert click_line in PyProject.get().senv.package.conda_lock_path.read_text()


def test_lock_throws_if_not_all_platform_exists(
    temp_appdirs_pyproject, cli_runner, fake_combined_lock
):
    with cd(temp_appdirs_pyproject.parent):
        fake_linux_lock_path = Path("my_lock_file_linux-64.lock")
        fake_linux_lock_path.write_text(fake_combined_lock.json(indent=2))
        result = cli_runner.invoke(
            app,
            [
                "package",
                "-f",
                str(temp_appdirs_pyproject),
                "lock",
                "--platforms",
                "osx-64",
                "--platforms",
                "win-64",
                "--platforms",
                "linux-64",
                "--based-on-tested-lock-file",
                str(fake_linux_lock_path.resolve()),
            ],
        )
        assert result.exit_code != 0
        assert isinstance(result.exception, SenvNotAllPlatformsInBaseLockFile)
        assert set(result.exception.missing_platforms) == {"osx-64", "win-64"}
