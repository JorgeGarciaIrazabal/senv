from pysenv.settings.config import Config


def get_default_build_system():
    return Config.get().pysenv.venv.build_system


def get_conda_platforms():
    return list(Config.get().pysenv.venv.conda_lock_platforms)
