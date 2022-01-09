from typing import List

from senv.pyproject import BuildSystem, PyProject


def get_default_env_build_system() -> BuildSystem:
    return PyProject.get().senv.env.build_system


def get_default_package_build_system() -> BuildSystem:
    return PyProject.get().senv.package.build_system


def get_conda_platforms() -> List[str]:
    return list(PyProject.get().senv.env.conda_lock_platforms)


def get_conda_channels() -> List[str]:
    return PyProject.get().senv.conda_channels


def get_locked_app_name() -> str:
    return f"{PyProject.get().package_name}_app"
