import tarfile
from pathlib import Path
from typing import Optional

from pytest import fixture

from senv.conda_publish import LockFileMetaData
from senv.errors import SenvNotAllPlatformsInBaseLockFile
from senv.main import app
from senv.pyproject import PyProject
from senvx.models import CombinedCondaLock

from senv.pyproject_to_conda import LOCKED_PACKAGE_LOCK_NAME
from senv.tests.conftest import STATIC_PATH
from senv.utils import cd

__appdirs_lock_content: Optional[str] = None


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
        PyProject.get().senv.env.conda_lock_path.write_text(
            (STATIC_PATH / "appdirs_combined_lock.json").read_text()
        )
        return PyProject.get().senv.env.conda_lock_path.resolve()


# todo mock conda build and move it to unit test
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
        assert "click-8.0.3" in PyProject.get().senv.package.conda_lock_path.read_text()


def test_publish_locked_packaged(
    temp_appdirs_pyproject, cli_runner, appdirs_env_lock_path, mocker, tmp_path
):
    mocker.patch("senv.package.publish_conda")
    build_path = PyProject.get().senv.package.conda_build_path

    with cd(temp_appdirs_pyproject.parent):
        result = cli_runner.invoke(
            app,
            [
                "package",
                "-f",
                str(temp_appdirs_pyproject),
                "publish-locked",
                "--repository-url",
                "no-url",
                "--username",
                "test",
                "--password",
                "test",
                "-l",
                str(appdirs_env_lock_path),
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        tar_file = build_path / "noarch" / "appdirs__locked-1.1.4-0.tar.bz2"
        extract_path = temp_appdirs_pyproject.parent / "extract"
        extract_path.mkdir()

        assert build_path
        assert tar_file.exists()
        with tarfile.open(str(tar_file)) as t:
            t.extractall(str(extract_path))

        assert (extract_path / LOCKED_PACKAGE_LOCK_NAME).exists()
        assert (
            extract_path / LOCKED_PACKAGE_LOCK_NAME
        ).read_text() == appdirs_env_lock_path.read_text()


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
