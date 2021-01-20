import os
import subprocess
from pathlib import Path
from sys import platform
from tempfile import TemporaryDirectory
from typing import Optional

import filelock
import requests
import typer
from ensureconda import ensureconda

from senvx.models import LockFileMetaData, SenvxMalformedAppLockFile, Settings

app = typer.Typer(no_args_is_help=True, add_completion=False)


def current_platform() -> str:
    if platform == "linux" or platform == "linux2":
        return "linux-64"
    elif platform == "darwin":
        return "osx-64"
    elif platform == "win32":
        return "win-64"
    else:
        raise NotImplementedError(f"Platform {platform} not supported")


def _install_from_lock_file_template(
    package_name: Optional[str], lock_url: str
) -> None:
    settings = Settings()
    with TemporaryDirectory(prefix="senvx-") as tmp_dir:
        lock_path = Path(tmp_dir, "lock_file.lock")
        lock_path.write_bytes(requests.get(lock_url, allow_redirects=True).content)
        try:
            metadata = LockFileMetaData.from_lock_path(lock_path)
            metadata.package_name = package_name or metadata.package_name
        except SenvxMalformedAppLockFile:
            if package_name is None:
                typer.Abort("No package_name or metadata found in lockfile")
            metadata = LockFileMetaData(package_name=package_name)

        entry_points_conflicts = []
        for entrypoint in metadata.entry_points:
            if Path(settings.BIN_DIR / entrypoint).exists():
                entry_points_conflicts.append(entrypoint)
        if len(entry_points_conflicts) > 0:
            if not typer.confirm(
                f"Entry points {entry_points_conflicts} "
                f"already exists in {settings.BIN_DIR.resolve()}.\n"
                "Do you want to overwrite them?"
            ):
                typer.Abort()

        conda_exe = ensureconda(no_install=True, micromamba=False, mamba=False)
        prefix = settings.INSTALLATION_PATH.resolve() / metadata.package_name
        subprocess.check_call(
            [
                conda_exe,
                "create",
                "-y",
                "--prefix",
                str(prefix),
                "--file",
                str(lock_path.resolve()),
            ]
        )

        typer.echo(f"Installed {metadata.package_name } in {prefix.resolve()}")

        for entrypoint in metadata.entry_points:
            dst = Path(settings.BIN_DIR / entrypoint)
            src = prefix / entrypoint
            dst.unlink(missing_ok=True)
            os.symlink(src, dst)


@app.command(no_args_is_help=True)
def install(
    package_name: Optional[str] = typer.Argument(...),
    lock_url_template: Optional[str] = typer.Option(
        None,
        "-l",
        "--lock-url-template",
        help='lock file url template where "{platform}" will be replace with the current platform ',
    ),
):
    # if not any([package_name, lock_url_template]):
    #     raise typer.Abort("Either package_name or lock_url_template have to be provided")
    # if all([package_name, lock_url_template]):
    #     raise typer.Abort("Only one of package or lock_url_template can be provided")
    settings = Settings()
    app_path = Path(settings.INSTALLATION_PATH)
    app_path.mkdir(parents=True, exist_ok=True)
    with filelock.FileLock(str(app_path / "installing.lock"), timeout=60 * 5):
        if lock_url_template:
            lock_url = lock_url_template.replace("{platform}", current_platform())
            _install_from_lock_file_template(package_name, lock_url)


if __name__ == "__main__":
    app()
