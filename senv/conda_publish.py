import os
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from shutil import which
from typing import List, Optional

import requests
import typer
from conda_lock.conda_lock import run_lock
from conda_lock.src_parser.pyproject_toml import normalize_pypi_name

from senv.errors import SenvNotAllPlatformsInBaseLockFile
from senv.log import log
from senv.pyproject import PyProject
from senv.pyproject_to_conda import combine_conda_lock_files, create_env_yaml
from senvx.errors import SenvxMalformedAppLockFile
from senvx.main import install_from_lock
from senvx.models import CombinedCondaLock, LockFileMetaData
from senv.utils import cd_tmp_dir, confirm


def _install_package_dependencies():
    confirm(
        "some dependencies are required to publish packages,"
        " Do you want install them independently using senvx?",
        abort=True,
    )
    install_from_lock(
        Path(__file__).parent
        / "dynamic_dependencies"
        / "senv_package_tools"
        / "conda_env.lock.json"
    )


def set_conda_build_path():
    PyProject.get().senv.package.conda_build_path.mkdir(parents=True, exist_ok=True)
    os.environ["CONDA_BLD_PATH"] = str(PyProject.get().senv.package.conda_build_path)


def build_conda_package_from_recipe(
    meta_path: Path, python_version: Optional[str] = None
):
    set_conda_build_path()
    if which("conda-mambabuild") is None:
        _install_package_dependencies()
    args = ["conda-mambabuild", "--override-channels"]
    for c in PyProject.get().senv.conda_channels:
        args += ["--channel", c]
    if python_version:
        args.extend(["--python", python_version])
    result = subprocess.run(args + [str(meta_path.parent)])
    if result.returncode != 0:
        raise typer.Abort("Failed building conda package")


def publish_conda(
    username: str,
    password: str,
    repository_url: str,
    package_name: Optional[str] = None,
):
    c = PyProject.get()
    conda_dist = c.senv.package.conda_build_path
    files_to_upload = list(
        conda_dist.glob(f"*/{package_name or c.package_name}-{c.version}*.tar.bz2")
    )
    if len(files_to_upload) == 0:
        log.warning(
            f'No files found to upload in "{conda_dist}",'
            " you need to build the package before uploading it"
        )
        raise typer.Abort()

    # todo we might need to be more specific here
    if repository_url.endswith("anaconda.org"):
        return publish_conda_to_anaconda_org(username, password, files_to_upload)

    for tar_path in files_to_upload:
        package = tar_path.name
        arch = tar_path.parent.name
        dest = f"{repository_url}/{arch}/{package}"
        resp = requests.head(dest)
        if resp.status_code != 404:
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


def publish_conda_to_anaconda_org(
    username: str, password: str, files_to_upload: List[Path]
):
    if which("anaconda") is None:
        _install_package_dependencies()
    if which("anaconda") is None:
        raise typer.Abort("Failed installing anaconda")

    # todo maybe to intrusive?
    subprocess.check_call(["anaconda", "logout"])
    subprocess.check_call(
        ["anaconda", "login", "--username", username, "--password", password]
    )
    for file_to_upload in files_to_upload:
        subprocess.check_call(["anaconda", "upload", str(file_to_upload.resolve())])


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
        with ProcessPoolExecutor() as executor:
            for platform in platforms_set:
                tar_urls = combined_lock.platform_tar_links[platform]
                # add the current package
                dependencies = [
                    f"{c.package_name}={c.version}",
                ]
                # pin version for all direct dependencies
                for line in tar_urls:
                    channel, dep = line.rsplit("/", 1)
                    name, version, _ = dep.rsplit("-", 2)
                    if name.lower() in direct_dependencies_name:
                        dependencies.append(f"{name}={version}")
                yaml_path = create_env_yaml(
                    channels=conda_channels,
                    output=Path(tmp_dir) / platform / "env.yaml",
                    dependencies=dependencies,
                )
                executor.submit(
                    run_lock,
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
