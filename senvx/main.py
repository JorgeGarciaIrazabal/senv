import subprocess
from pathlib import Path
from sys import platform
from tempfile import TemporaryDirectory
from typing import Optional

import appdirs
import filelock
import requests
import typer
from ensureconda import ensureconda
from pydantic import BaseSettings, Field

app = typer.Typer(no_args_is_help=True, add_completion=False)


class Settings(BaseSettings):
    INSTALLATION_PATH: Path = Field(Path(appdirs.user_data_dir("senvx")))
    BIN_DIR: Path = Field(Path.home() / ".local" / "bin")

    class Config:
        env_prefix = "SENVX_"


def current_platform() -> str:
    if platform == "linux" or platform == "linux2":
        return "linux-64"
    elif platform == "darwin":
        return "osx-64"
    elif platform == "win32":
        return "win-64"
    else:
        raise NotImplementedError(f"Platform {platform} not supported")


def _install_from_lock_file_template(package_name, lock_url: str) -> None:
    settings = Settings()
    with TemporaryDirectory(prefix="senvx-") as tmp_dir:
        lock_path = Path(tmp_dir, "lock_file.lock")
        lock_path.write_bytes(requests.get(lock_url, allow_redirects=True).content)
        conda_exe = ensureconda(no_install=True, micromamba=False, mamba=False)
        prefix = settings.INSTALLATION_PATH.resolve() / package_name
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

        typer.echo(f"Installed {package_name} in {prefix.resolve()}")

        # todo get entrypoints from lockfile


@app.command()
def install(
    package_name: str = typer.Argument(...),
    lock_url_template: Optional[str] = typer.Option(..., "-l"),
):
    # if not any([package_name, lock_url_template]):
    #     raise typer.Abort("Either package_name or lock_url_template have to be provided")
    # if all([package_name, lock_url_template]):
    #     raise typer.Abort("Only one of package or lock_url_template can be provided")

    app_path = Path(appdirs.user_data_dir("senvx"))
    app_path.mkdir(parents=True, exist_ok=True)
    with filelock.FileLock(str(app_path / "installing.lock"), timeout=60 * 5):
        if lock_url_template:
            lock_url = lock_url_template.replace("{platform}", current_platform())
            _install_from_lock_file_template(package_name, lock_url)


if __name__ == "__main__":
    app()
