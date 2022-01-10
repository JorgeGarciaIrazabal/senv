import os
from pathlib import Path
from shutil import copyfile

from pytest import fixture
from typer.testing import CliRunner

from senv.pyproject import PyProject

TESTS_PATH = Path(__file__).parent.resolve()
STATIC_PATH = TESTS_PATH / "static"


@fixture()
def cli_runner(tmp_path):
    return CliRunner()


@fixture()
def build_temp_pyproject(tmp_path: Path, mocker):
    mocker.patch.dict(
        os.environ,
        {"SENV_CONDA_BUILD_PATH": str((tmp_path / "test_conda_build").resolve())},
    )

    def _build_temp_pyproject(pyproject_path: Path):
        temp_path = tmp_path / "test_project" / "pyproject.toml"
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        copyfile(pyproject_path, temp_path)
        c = PyProject.read_toml(temp_path)
        project = temp_path.parent / c.package_name.replace("-", "_") / "main.py"
        project.parent.mkdir(parents=True, exist_ok=True)
        project.write_text("print('hello world')")
        return temp_path

    return _build_temp_pyproject
