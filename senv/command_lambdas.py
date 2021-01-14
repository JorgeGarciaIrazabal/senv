from typing import List

from senv.config import BuildSystem, Config


def get_default_build_system() -> BuildSystem:
    return Config.get().senv.venv.build_system


def get_conda_platforms() -> List[str]:
    return list(Config.get().senv.venv.conda_lock_platforms)


def get_conda_channels() -> List[str]:
    return Config.get().senv.conda_channels


def get_locked_app_name() -> str:
    return f"{Config.get().package_name}_app"
