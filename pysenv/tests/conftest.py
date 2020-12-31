from pathlib import Path
from pytest import fixture
from typer.testing import CliRunner

TESTS_PATH = Path(__file__).parent.resolve()
STATIC_PATH = TESTS_PATH / "static"


@fixture()
def cli_runner(tmp_path):
    return CliRunner()
