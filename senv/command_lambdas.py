from senv.config import Config


def get_default_build_system():
    return Config.get().senv.venv.build_system


def get_conda_platforms():
    return list(Config.get().senv.venv.conda_lock_platforms)
