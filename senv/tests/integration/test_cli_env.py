from pytest import fixture

from senv.commands.settings_writer import AllowedConfigKeys, set_new_setting_value
from senv.main import app
from senv.pyproject import PyProject
from senvx.models import CombinedCondaLock
from senv.tests.conftest import STATIC_PATH
from senv.utils import cd

PYPROJECT_TOML = STATIC_PATH / "with_conda_channels_pyproject.toml"


@fixture()
def temp_pyproject(build_temp_pyproject):
    return build_temp_pyproject(PYPROJECT_TOML)


def test_env_locks_builds_the_lock_files_in_default_env_lock_files(
    temp_pyproject, cli_runner
):
    with cd(temp_pyproject.parent):
        result = cli_runner.invoke(
            app,
            [
                "env",
                "-f",
                str(temp_pyproject),
                "lock",
                "--platforms",
                "linux-64",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        lock_file = PyProject.get().senv.env.__fields__["conda_lock_path"].default
        assert lock_file.exists()

        combined_lock = CombinedCondaLock.parse_file(lock_file)
        assert set(combined_lock.platform_tar_links.keys()) == {"linux-64"}


def test_env_locks_builds_the_lock_files_in_the_configured_directory(
    temp_pyproject, cli_runner
):
    lock_file = temp_pyproject.parent / "my_lock_folder"
    PyProject.read_toml(temp_pyproject)
    set_new_setting_value(AllowedConfigKeys.CONDA_ENV_LOCK_PATH, str(lock_file))
    result = cli_runner.invoke(
        app,
        [
            "env",
            "-f",
            str(temp_pyproject),
            "lock",
            "--platforms",
            "osx-64",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert lock_file.exists()
    combined_lock = CombinedCondaLock.parse_file(lock_file)

    assert set(combined_lock.platform_tar_links.keys()) == {"osx-64"}
