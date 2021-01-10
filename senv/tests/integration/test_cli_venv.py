from shutil import copyfile

from pytest import fixture

from senv.main import app
from senv.settings.config import Config
from senv.settings.settings_writer import AllowedConfigKeys, set_new_setting_value
from senv.tests.conftest import STATIC_PATH
from senv.utils import cd

PYPROJECT_TOML = STATIC_PATH / "with_conda_channels_pyproject.toml"


@fixture()
def temp_pyproject(tmp_path):
    simple_pyproject = PYPROJECT_TOML
    temp_path = tmp_path / "pyproject.toml"
    copyfile(simple_pyproject, temp_path)
    return temp_path


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
