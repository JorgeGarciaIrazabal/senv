import shutil
from pathlib import Path
from typing import Optional

from senv.conda_publish import build_conda_package_from_recipe, publish_conda
from senv.pyproject import PyProject
from senv.pyproject_to_conda import LOCKED_PACKAGE_LOCK_NAME, locked_package_to_recipe_yaml
from senv.utils import MySpinner, cd, cd_tmp_dir


def conda_publish_locked_package(
    *,
    repository_url: Optional[str] = None,
    username: str,
    password: str,
    lock_file: Path
):
    c: PyProject = PyProject.get()

    with cd_tmp_dir() as tmp_dir, MySpinner("Building temp files") as status:
        status.start()
        meta_path = tmp_dir / "conda.recipe" / "meta.yaml"
        temp_lock_path = tmp_dir / LOCKED_PACKAGE_LOCK_NAME
        meta_path.parent.mkdir(parents=True)
        shutil.copyfile(str(lock_file.absolute()), str(temp_lock_path.absolute()))

        locked_package_to_recipe_yaml(temp_lock_path, meta_path)

        status.writeln("Building conda package")
        build_conda_package_from_recipe(meta_path.absolute())

        with cd(meta_path.parent):
            repository_url = repository_url or c.senv.package.conda_publish_url
            status.writeln(f"Publishing to {repository_url}")
            publish_conda(
                username,
                password,
                repository_url,
                package_name=c.package_name_locked,
            )
