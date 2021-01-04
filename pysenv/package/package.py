import os
import subprocess
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import Optional

import typer

from pysenv.command_lambdas import get_default_build_system
from pysenv.log import log
from pysenv.settings.config import BuildSystem, Config
from pysenv.utils import cd
from pysenv.venv.pyproject_to_conda import pyproject_to_recipe_yaml

app = typer.Typer()


@app.command(name="build")
def build_package(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    python_version: Optional[str] = None,
):
    if build_system == BuildSystem.POETRY:
        with cd(Config.get().config_path.parent):
            subprocess.check_call([Config.get().poetry_path, "build"])
    elif build_system == BuildSystem.CONDA:
        # conda build -m ${CONDA_VARIANT} --no-test conda.recipe
        if which("conda-build") is None:
            log.warn("conda build not found, install conda-build")
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
            else:
                raise typer.Abort()
        dist_conda = Config.get().config_path.parent / "dist_conda"
        dist_conda.mkdir(parents=True, exist_ok=True)
        os.environ["CONDA_BLD_PATH"] = str(dist_conda)
        args = ["conda-build", "--no-test"]
        for c in Config.get().pysenv.conda_channels:
            args += ["-c", c]
        with TemporaryDirectory(prefix="pysenv_") as tmpdir:
            meta_path = Path(tmpdir) / "meta.yaml"
            pyproject_to_recipe_yaml(python_version=python_version, output=meta_path)
            if python_version:
                args.extend(["--python", python_version])
            result = subprocess.run(args + [str(meta_path.parent)])
            if result.returncode != 0:
                raise typer.Abort()
    else:
        raise NotImplementedError()
