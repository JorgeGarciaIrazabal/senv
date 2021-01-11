import os
import subprocess
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import Optional

import typer

from senv.command_lambdas import get_default_build_system
from senv.commands.config import BuildSystem, Config
from senv.log import log
from senv.pyproject_to_conda import pyproject_to_recipe_yaml
from senv.utils import cd, tmp_env

app = typer.Typer()


def _ensure_conda_build():
    if which("conda-build") is None:
        log.warning("conda build not found, install conda-build")
        if typer.confirm("Do you want to install it?"):
            log.info("Installing conda-build")
            subprocess.check_call(
                [
                    Config.get().conda_path,
                    "install",
                    "conda-build",
                    "-c",
                    "conda-forge",
                    "-y",
                ]
            )
            return subprocess.check_output(
                [Config.get().conda_path, "run", "which", "conda-build"]
            ).strip()
        else:
            raise typer.Abort()
    return which("conda-build")


def _set_conda_build_path():
    Config.get().senv.conda_build_root.mkdir(parents=True, exist_ok=True)
    os.environ["CONDA_BLD_PATH"] = str(Config.get().senv.conda_build_root)


@app.command(name="build")
def build_package(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    python_version: Optional[str] = None,
):
    if build_system == BuildSystem.POETRY:
        with cd(Config.get().config_path.parent):
            subprocess.check_call([Config.get().poetry_path, "build"])
    elif build_system == BuildSystem.CONDA:
        conda_build_path = _ensure_conda_build()
        with tmp_env(), cd(Config.get().config_path.parent):
            _set_conda_build_path()
            args = [conda_build_path, "--no-test"]
            for c in Config.get().senv.conda_channels:
                args += ["-c", c]
            with TemporaryDirectory(prefix="senv_") as tmpdir:
                meta_path = Path(tmpdir) / "meta.yaml"
                pyproject_to_recipe_yaml(
                    python_version=python_version, output=meta_path
                )
                if python_version:
                    args.extend(["--python", python_version])
                result = subprocess.run(args + [str(meta_path.parent)])
                if result.returncode != 0:
                    raise typer.Abort("Failed building conda package")
    else:
        raise NotImplementedError()


@app.command(name="publish")
def publish_package(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    python_version: Optional[str] = None,
    build: bool = False,
    repository_url: Optional[str] = None,
    username: str = typer.Option(None, envvar="SENV_PUBLISHER_USERNAME"),
    password: str = typer.Option(None, envvar="SENV_PUBLISHER_PASSWORD"),
):
    if build:
        build_package(build_system=build_system, python_version=python_version)
    if build_system == BuildSystem.POETRY:
        with cd(Config.get().config_path.parent):
            if repository_url is not None:
                subprocess.check_call(
                    [
                        Config.get().poetry_path,
                        "config",
                        f"repositories.senv_{Config.get().package_name}",
                        repository_url,
                    ]
                )
            args = [Config.get().poetry_path, "publish"]
            if username and password:
                args += ["--username", username, "--password", password]
            subprocess.check_call(args)
    elif build_system == BuildSystem.CONDA:
        with cd(Config.get().config_path.parent):
            # todo, this is super specific to our case, we need to make this more generic
            if repository_url is None:
                raise NotImplementedError(
                    "repository_url is required to publish a conda environment. "
                    "Only private channels are currently allowed"
                )
    else:
        raise NotImplementedError()
