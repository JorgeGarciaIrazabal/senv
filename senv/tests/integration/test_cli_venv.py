from pytest import fixture

from senv.commands.settings_writer import AllowedConfigKeys, set_new_setting_value
from senv.main import app
from senv.pyproject import PyProject
from senv.tests.conftest import STATIC_PATH
from senv.utils import cd

PYPROJECT_TOML = STATIC_PATH / "with_conda_channels_pyproject.toml"


@fixture()
def temp_pyproject(build_temp_pyproject):
    return build_temp_pyproject(PYPROJECT_TOML)


def test_venv_locks_builds_the_lock_files_in_default_venv_lock_files(
    temp_pyproject, cli_runner
):
    with cd(temp_pyproject.parent):
        result = cli_runner.invoke(
            app,
            [
                "venv",
                "lock",
                "--platforms",
                "linux-64",
                "-f",
                str(temp_pyproject),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert (
            PyProject.get().senv.venv.__fields__["venv_lock_dir"].default
            / "conda-linux-64.lock"
        ).exists()


def test_venv_locks_builds_the_lock_files_in_the_configured_directory(
    temp_pyproject, cli_runner
):
    lock_dir = temp_pyproject.parent / "my_lock_folder"
    PyProject.read_toml(temp_pyproject)
    set_new_setting_value(AllowedConfigKeys.VENV_LOCK_DIRECTORY, str(lock_dir))
    result = cli_runner.invoke(
        app,
        [
            "venv",
            "lock",
            "--platforms",
            "osx-64",
            "-f",
            str(temp_pyproject),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (lock_dir / "conda-osx-64.lock").exists()
