import contextlib
import os
import shutil
import sys
from io import StringIO
from os import devnull
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator

from senv.pyproject import PyProject


@contextlib.contextmanager
def cd(path: Path):
    cwd = os.getcwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(cwd)


@contextlib.contextmanager
def cd_tmp_dir(prefix="senv_") -> Iterator[Path]:
    with TemporaryDirectory(prefix=prefix) as tmp_dir, cd(Path(tmp_dir)):
        yield Path(tmp_dir)


@contextlib.contextmanager
def tmp_env() -> None:
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


@contextlib.contextmanager
def tmp_repo() -> Iterator[PyProject]:
    """
    duplicate repository in temporary directory and point PyProject to this new path
    This is useful if we want to make temporary modifications
    for long running tasks or that can fail.
    That way no temporary change will never affect the real repository
    :return:
    """
    # this might not be very realistic for very big projects
    original_config_path = PyProject.get().config_path
    with cd_tmp_dir(prefix="senv_tmp_repo-") as tmp_dir:
        project_dir = Path(tmp_dir, "project")
        shutil.copytree(PyProject.get().config_path.parent, project_dir)
        PyProject.read_toml(Path(project_dir, "pyproject.toml"))
        yield PyProject.get()
    PyProject.read_toml(original_config_path)


@contextlib.contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(devnull, "w") as fnull, contextlib.redirect_stderr(
        fnull
    ) as err, contextlib.redirect_stdout(fnull) as out:
        yield err, out


class Hider:
    def __init__(self, channels=("stdout",)):
        self._stomach = StringIO()
        self._orig = {ch: None for ch in channels}

    def __enter__(self):
        for ch in self._orig:
            self._orig[ch] = getattr(sys, ch)
            setattr(sys, ch, self)
        return self

    def write(self, string):
        self._stomach.write(string)

    def flush(self):
        pass

    def autopsy(self):
        return self._stomach.getvalue()

    def __exit__(self, *args):
        for ch in self._orig:
            setattr(sys, ch, self._orig[ch])
