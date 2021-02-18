import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
import typer

from senv.senvx.main import install
from senv.senvx.models import Settings
from senv.senvx.tests.conftest import STATIC_PATH

BLACK_METADATA_LOCK = STATIC_PATH / "black-with-meta.lock.json"
BLACK_NO_NAME_LOCK = STATIC_PATH / "black-with-no-name.lock.json"
BLACK_CORRUPTED_LOCK = STATIC_PATH / "black-corrupted.lock.json"
BLACK_STANDARD_LOCK = STATIC_PATH / "black-corrupted.lock.json"


@pytest.fixture(autouse=True)
def mock_request(mocker):
    return mocker.patch.object(
        requests,
        "get",
        new=lambda path, **kwargs: (MagicMock(content=Path(path).read_bytes())),
    )


@pytest.fixture()
def mock_subprocess_call(mocker) -> MagicMock:
    call_mock: MagicMock = mocker.patch("subprocess.call")
    call_mock.return_value = 0
    yield call_mock


@pytest.fixture()
def assert_no_subprocess_is_called(mock_subprocess_call) -> MagicMock:
    mock_subprocess_call.return_value = None
    yield mock_subprocess_call
    mock_subprocess_call.assert_not_called()


@pytest.fixture()
def confirm_mock(mocker) -> MagicMock:
    return mocker.patch("typer.confirm")


@pytest.fixture(autouse=True)
def mock_settings(mocker, tmpdir_factory):
    tmp_dir = tmpdir_factory.mktemp("senvx-")
    mocker.patch.dict(
        os.environ,
        {
            "SENVX_INSTALLATION_PATH": str(tmp_dir / "installation"),
            "SENVX_BIN_DIR": str(tmp_dir / "bin"),
        },
    )
    settings = Settings()
    assert settings.INSTALLATION_PATH == tmp_dir / "installation"
    assert settings.BIN_DIR == tmp_dir / "bin"
    settings.INSTALLATION_PATH.mkdir(parents=True)
    settings.BIN_DIR.mkdir(parents=True)


@pytest.fixture()
def black_fake_entry_points():
    settings = Settings()
    install_bin = settings.INSTALLATION_PATH / "black" / "bin"
    install_bin.mkdir(parents=True)
    (install_bin / "black").write_text("test")
    (install_bin / "blackd").write_text("test")


def tests_install_does_not_ask_to_fix_conflicts_if_there_are_none(
    mock_subprocess_call, confirm_mock, black_fake_entry_points
):
    install(str(BLACK_METADATA_LOCK), None, None)
    confirm_mock.assert_not_called()

    assert (Settings().BIN_DIR / "black").exists()
    assert (Settings().BIN_DIR / "blackd").exists()


def tests_install_confirm_with_conflicts_overwrites_existing_symlinks(
    mock_subprocess_call, confirm_mock, black_fake_entry_points
):
    confirm_mock.return_value = True
    (Settings().BIN_DIR / "black").write_text("original_bin")

    install(str(BLACK_METADATA_LOCK), None, None)
    confirm_mock.assert_called()

    assert (
        Settings().BIN_DIR / "black"
    ).read_text() == "test", "black should be overwritten"
    assert (Settings().BIN_DIR / "blackd").exists()


def tests_install_not_confirm_with_conflicts_should_keep_original_state(
    mock_subprocess_call, confirm_mock, black_fake_entry_points
):
    confirm_mock.return_value = False
    (Settings().BIN_DIR / "black").write_text("original_bin")

    with pytest.raises(typer.Abort):
        install(str(BLACK_METADATA_LOCK), None, None)
    confirm_mock.assert_called()

    assert (
        Settings().BIN_DIR / "black"
    ).read_text() == "original_bin", "black should stay they same as before"
    assert not (Settings().BIN_DIR / "blackd").exists()


def tests_install_continue_if_there_are_missing_entry_points_generate_the_other_ones(
    mock_subprocess_call, confirm_mock, black_fake_entry_points
):
    confirm_mock.return_value = True
    (Settings().INSTALLATION_PATH / "black" / "bin" / "blackd").unlink()
    install(str(BLACK_METADATA_LOCK), None, None)
    confirm_mock.assert_called()

    assert (Settings().BIN_DIR / "black").exists()
    assert not (Settings().BIN_DIR / "blackd").exists()

    assert (
        Settings().INSTALLATION_PATH / "black"
    ).exists(), "environment should exist still"


def tests_install_abort_on_missing_entry_points_removes_env_path_and_entry_points(
    mock_subprocess_call, confirm_mock, black_fake_entry_points
):
    confirm_mock.return_value = False
    (Settings().INSTALLATION_PATH / "black" / "bin" / "blackd").unlink()
    with pytest.raises(typer.Abort):
        install(str(BLACK_METADATA_LOCK), None, None)
    confirm_mock.assert_called()

    assert not (Settings().BIN_DIR / "black").exists()
    assert not (Settings().BIN_DIR / "blackd").exists()

    assert not (
        Settings().INSTALLATION_PATH / "black"
    ).exists(), "environment should not exist"


def tests_lock_metadata_gets_overwritten_if_package_name_is_provided(
    mock_subprocess_call, black_fake_entry_points
):
    # moving entry_points to new package_name
    shutil.move(
        Settings().INSTALLATION_PATH / "black",
        Settings().INSTALLATION_PATH / "new_black",
    )
    # make sure we mock env in the new path
    assert not (Settings().INSTALLATION_PATH / "black").exists()
    assert (Settings().INSTALLATION_PATH / "new_black").exists()

    install(str(BLACK_METADATA_LOCK), package_name="new_black", entry_points=None)

    # entry_points where found in new env
    assert (Settings().BIN_DIR / "black").exists()
    assert (Settings().BIN_DIR / "blackd").exists()


def tests_lock_metadata_gets_overwritten_if_entry_points_is_provided(
    mock_subprocess_call, black_fake_entry_points
):
    install(str(BLACK_METADATA_LOCK), package_name=None, entry_points=["black"])

    # entry_points where found in new env
    assert (Settings().BIN_DIR / "black").exists()
    assert not (Settings().BIN_DIR / "blackd").exists()


def tests_package_name_is_required(mock_subprocess_call, black_fake_entry_points):
    with pytest.raises(typer.Exit) as e:
        install(str(BLACK_NO_NAME_LOCK), package_name=None, entry_points=None)

    assert "package name is required" in str(e)


def tests_corrupted_meta_requires_package_name(
    mock_subprocess_call, black_fake_entry_points
):
    with pytest.raises(typer.Exit) as e:
        install(str(BLACK_CORRUPTED_LOCK), package_name=None, entry_points=None)

    try:
        install(
            str(BLACK_CORRUPTED_LOCK),
            package_name="new_package_name",
            entry_points=None,
        )
    except e:
        raise pytest.fail(f"Not expected raise with package_name {e}")


def tests_standard_lock_file_needs_package_name(
    mock_subprocess_call, black_fake_entry_points
):
    with pytest.raises(typer.Exit) as e:
        install(str(BLACK_STANDARD_LOCK), package_name=None, entry_points=None)

    try:
        install(
            str(BLACK_STANDARD_LOCK),
            package_name="new_package_name",
            entry_points=None,
        )
    except e:
        raise pytest.fail(f"Not expected raise with package_name {e}")
