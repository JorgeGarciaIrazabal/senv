import contextlib
import os
from pathlib import Path


@contextlib.contextmanager
def cd(path: Path):
    cwd = os.getcwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(cwd)


@contextlib.contextmanager
def tmp_env():
    """
    Temporarily set the process environment variables.

    >>> with tmp_env():
    ...   "PLUGINS_DIR" in os.environ
    False
    >>> with tmp_env():
    ...   os.environ["PLUGINS_DIR"] = "tmp"
    ...   "PLUGINS_DIR" in os.environ
    True
    >>> "PLUGINS_DIR" in os.environ
    False

    """
    old_environ = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)
