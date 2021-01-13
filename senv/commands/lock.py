from copy import deepcopy
from typing import List, Optional

import typer
from conda_lock.conda_lock import run_lock

from senv.command_lambdas import get_conda_platforms, get_default_build_system
from senv.commands.settings_writer import set_config_value_to_pyproject
from senv.commands.venv import lock
from senv.config import BuildSystem, Config
from senv.pyproject_to_conda import pyproject_to_recipe_yaml
from senv.utils import cd, tmp_env, tmp_repo

app = typer.Typer()


@app.command()
def venv(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    platforms: List[str] = typer.Option(
        get_conda_platforms,
        case_sensitive=False,
        help="conda platforms, for example osx-64 or linux-64",
    ),
):
    lock(build_system, platforms)


@app.command(name="app")
def lock_app(
    build_system: BuildSystem = typer.Option(get_default_build_system),
    platforms: List[str] = typer.Option(
        get_conda_platforms,
        case_sensitive=False,
        help="conda platforms, for example osx-64 and/or linux-64",
    ),
    based_on_tested_lock_template: Optional[str] = typer.Option(
        None,
        help="Create the lock file with the same direct dependencies"
        " as the ones pinned in the lock template provided.\n"
        "For conda locks, this template should include `{platform}`"
        " so it can generate the right lock file.\n"
        "More information in {Todo: add link to documentation}",
    ),
    include_self: bool = typer.Option(
        False,
        help="Add the current project to the lock file. "
             "IMPORTANT! This assumes the conda package was already published",
    ),
):
    platforms = platforms
    if build_system == BuildSystem.POETRY:
        raise NotImplementedError()
    elif build_system == BuildSystem.CONDA:
        Config.get().senv.app_lock_dir.mkdir(exist_ok=True, parents=True)
        if based_on_tested_lock_template is None and not include_self:
            with cd(Config.get().senv.app_lock_dir):
                run_lock(
                    [pyproject_to_recipe_yaml()],
                    conda_exe=Config.get().conda_path,
                    platforms=platforms,
                    include_dev_dependencies=False,
                )
        elif include_self:
            with tmp_env(), tmp_repo() as config:
                deps = deepcopy(config.dependencies)
                deps[config.package_name] = f"=={config.version}"
                set_config_value_to_pyproject(
                    config.config_path,
                    "tools.senv.dependencies",
                    config.dependencies + [],
                )
            if not based_on_tested_lock_template:
                with cd(config.senv.app_lock_dir):
                    run_lock(
                        [pyproject_to_recipe_yaml()],
                        conda_exe=config.conda_path,
                        platforms=platforms,
                        include_dev_dependencies=False,
                    )
            else:
                pass
                # Do the magic!!

    else:
        raise NotImplementedError()
