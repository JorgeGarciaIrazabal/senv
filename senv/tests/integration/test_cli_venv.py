from pytest import fixture

from senv.commands.config import Config
from senv.main import app
from senv.settings_writer import AllowedConfigKeys, set_new_setting_value
from senv.tests.conftest import STATIC_PATH
from senv.utils import cd

PYPROJECT_TOML = STATIC_PATH / "with_conda_channels_pyproject.toml"


@fixture()
def temp_pyproject(build_temp_pyproject):
    return build_temp_pyproject(PYPROJECT_TOML)


def test_venv_locks_builds_the_lock_files_working_directory_by_default(
    temp_pyproject, cli_runner
):
    with cd(temp_pyproject.parent):
        result = cli_runner.invoke(
            app, ["-f", str(temp_pyproject), "venv", "lock", "--platforms", "linux-64"]
        )
    assert result.exit_code == 0
    assert (temp_pyproject.parent / "conda-linux-64.lock").exists()


def test_venv_locks_builds_the_lock_files_in_the_configured_directory(
    temp_pyproject, cli_runner
):
    lock_dir = temp_pyproject.parent / "my_lock_folder"
    Config.read_toml(temp_pyproject)
    set_new_setting_value(AllowedConfigKeys.CONDA_LOCK_DIRECTORY, str(lock_dir))
    result = cli_runner.invoke(
        app, ["-f", str(temp_pyproject), "venv", "lock", "--platforms", "osx-64"]
    )
    assert result.exit_code == 0
    assert (lock_dir / "conda-osx-64.lock").exists()
