import os
import subprocess
from pathlib import Path
from shutil import which
from tempfile import TemporaryDirectory
from typing import List, Optional, Sequence

import requests
import typer
from conda_lock.conda_lock import run_lock
from conda_lock.src_parser.pyproject_toml import normalize_pypi_name

from senv.errors import SenvError, SenvNotAllRequiredLockFiles
from senv.log import log
from senv.pyproject import PyProject
from senv.pyproject_to_conda import create_env_yaml
from senv.utils import cd
from senvx.errors import SenvxMalformedAppLockFile
from senvx.models import LockFileMetaData


def ensure_conda_build():
    if which("conda-build") is None:
        log.warning("conda build not found, install conda-build")
        if typer.confirm("Do you want to install it?"):
            log.info("Installing conda-build")
            subprocess.check_call(
                [
                    PyProject.get().conda_path,
                    "install",
                    "conda-build",
                    "-c",
                    "conda-forge",
                    "-y",
                ]
            )
            return subprocess.check_output(
                [PyProject.get().conda_path, "run", "which", "conda-build"]
            ).strip()
        else:
            raise typer.Abort()
    return which("conda-build")


def set_conda_build_path():
    PyProject.get().senv.conda_build_path.mkdir(parents=True, exist_ok=True)
    os.environ["CONDA_BLD_PATH"] = str(PyProject.get().senv.conda_build_path)


def publish_conda(username: str, password: str, repository_url: str):
    conda_dist = PyProject.get().senv.conda_build_path
    for tar_path in conda_dist.glob(f"*/{PyProject.get().package_name}*.tar.bz2"):
        package = tar_path.name
        arch = tar_path.parent.name
        dest = f"{repository_url}/{arch}/{package}"
        resp = requests.head(dest)
        if resp.status_code == 404:
            log.warning("Object already exists not reuploading...")
        else:
            subprocess.check_call(
                [
                    "curl",
                    f"-u{username}:{password}",
                    "-T",
                    str(tar_path.resolve()),
                    dest,
                ],
            )


def build_lock_paths(based_on_tested_lock_files_template, platforms):
    lock_paths = {}
    if "{platform}" not in based_on_tested_lock_files_template:
        raise SenvError("no {platform} in 'based_on_tested_lock_files_template'")
    for platform in platforms:
        lock_paths[platform] = Path(
            based_on_tested_lock_files_template.replace("{platform}", platform)
        )
    missing_lock_files = [p for p in lock_paths.values() if not p.exists()]

    if len(missing_lock_files) > 0:
        raise SenvNotAllRequiredLockFiles(missing_lock_files)
    return lock_paths


def generate_app_lock_file_based_on_tested_lock_path(
    platform, lock_path, conda_channels
):
    direct_dependencies_name = {
        normalize_pypi_name(d).lower() for d in PyProject.get().senv.dependencies.keys()
    }
    # always include python even if it is not in the dependencies
    direct_dependencies_name.add("python")

    with cd(PyProject.get().senv.package_lock_dir), TemporaryDirectory() as tmp_dir:
        lock_str = lock_path.read_text()
        lock_str = lock_str.split("@EXPLICIT", 1)[1].strip()
        # add the current package
        dependencies = {
            PyProject.get().package_name: f"=={PyProject.get().version}",
        }
        # pin version for all direct dependencies
        for line in lock_str.splitlines(keepends=False):
            channel, dep = line.rsplit("/", 1)
            name, version, _ = dep.rsplit("-", 2)
            if name.lower() in direct_dependencies_name:
                dependencies[name] = f"=={version}"
        yaml_path = create_env_yaml(
            channels=conda_channels,
            output=Path(tmp_dir) / "env.yaml",
            dependencies=dependencies,
        )
        lock_file_with_metadata(
            [yaml_path],
            conda_exe=str(PyProject.get().conda_path),
            platforms=[platform],
        )


def lock_file_with_metadata(
    environment_files: List[Path],
    conda_exe: Optional[str],
    platforms: Optional[List[str]] = None,
    mamba: bool = False,
    micromamba: bool = False,
    include_dev_dependencies: bool = True,
    channel_overrides: Optional[Sequence[str]] = None,
):
    run_lock(
        environment_files=environment_files,
        conda_exe=conda_exe,
        platforms=platforms,
        mamba=mamba,
        micromamba=micromamba,
        include_dev_dependencies=include_dev_dependencies,
        channel_overrides=channel_overrides,
    )
    for platform in platforms:
        path = Path(f"conda-{platform}.lock")
        c = PyProject.get()
        LockFileMetaData(
            package_name=c.package_name,
            entry_points=list(c.senv.scripts.keys()),
        ).add_metadata_to_lockfile(path)


def _add_app_lockfile_metadata(lockfile: Path):
    lock_content = lockfile.read_text()
    if "@EXPLICIT" not in lock_content:
        raise SenvxMalformedAppLockFile("No @EXPLICIT found in lock file")
    lock_header, tars = lock_content.split("@EXPLICIT", 1)
    c = PyProject.get()
    metadata = LockFileMetaData(
        package_name=c.package_name,
        entry_points=list(c.senv.scripts.keys()),
    )
    meta_json = (
        "\n".join([f"# {l}" for l in metadata.json(indent=2).splitlines()]) + "\n"
    )
    lockfile.write_text(
        lock_header
        + "# @METADATA_INIT\n"
        + meta_json
        + "# @METADATA_END\n"
        + "@EXPLICIT\n"
        + tars
    )
