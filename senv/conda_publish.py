import os
import subprocess
from pathlib import Path
from typing import List

import requests
from conda_lock.conda_lock import run_lock
from conda_lock.src_parser.pyproject_toml import normalize_pypi_name

from senv.errors import SenvNotAllPlatformsInBaseLockFile
from senv.log import log
from senv.pyproject import PyProject
from senv.pyproject_to_conda import combine_conda_lock_files, create_env_yaml
from senv.utils import cd_tmp_dir
from senvx.errors import SenvxMalformedAppLockFile
from senvx.models import CombinedCondaLock, LockFileMetaData


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


def generate_app_lock_file_based_on_tested_lock_path(
    lock_path: Path, conda_channels: List[str], platforms: List[str]
) -> CombinedCondaLock:
    platforms_set = set(platforms)
    c = PyProject.get()
    direct_dependencies_name = {
        normalize_pypi_name(d).lower() for d in c.senv.dependencies.keys()
    }
    # always include python even if it is not in the dependencies
    direct_dependencies_name.add("python")

    combined_lock = CombinedCondaLock.parse_file(lock_path)
    combined_lock_platforms_set = set(combined_lock.platform_tar_links.keys())
    if not platforms_set.issubset(combined_lock_platforms_set):
        raise SenvNotAllPlatformsInBaseLockFile(
            platforms_set.difference(combined_lock_platforms_set)
        )

    with cd_tmp_dir() as tmp_dir:
        for platform in platforms_set:
            tar_urls = combined_lock.platform_tar_links[platform]
            # add the current package
            dependencies = {
                c.package_name: f"=={c.version}",
            }
            # pin version for all direct dependencies
            for line in tar_urls:
                channel, dep = line.rsplit("/", 1)
                name, version, _ = dep.rsplit("-", 2)
                if name.lower() in direct_dependencies_name:
                    dependencies[name] = f"=={version}"
            yaml_path = create_env_yaml(
                channels=conda_channels,
                output=Path(tmp_dir) / "env.yaml",
                dependencies=dependencies,
            )
            run_lock(
                [yaml_path],
                conda_exe=str(c.conda_path.resolve()),
                platforms=[platform],
            )
        return combine_conda_lock_files(tmp_dir, list(platforms))


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
