import contextlib
import os
from pathlib import Path
from sys import platform
from tempfile import TemporaryDirectory
from typing import Iterator

import typer

from senv.errors import SenvNotSupportedPlatform

__auto_confirm_yes = False


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
def auto_confirm_yes(yes: bool = False):
    global __auto_confirm_yes
    __auto_confirm_yes = yes
    yield
    __auto_confirm_yes = False


def confirm(
    text, default=False, abort=False, prompt_suffix=": ", show_default=True, err=False
):
    global __auto_confirm_yes
    if __auto_confirm_yes:
        return True
    return typer.confirm(
        text,
        default=default,
        abort=abort,
        prompt_suffix=prompt_suffix,
        show_default=show_default,
        err=err,
    )


def build_yes_option():
    return typer.Option(False, "--yes", "-y", help="Answer yes to all confirm prompts")


def get_current_platform() -> str:
    if platform == "linux" or platform == "linux2":
        return "linux-64"
    elif platform == "darwin":
        return "osx-64"
    elif platform == "win32":
        return "win-64"
    else:
        raise SenvNotSupportedPlatform(f"Platform {platform} not supported")
