import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

import pexpect
from pexpect import spawn
from shellingham import ShellDetectionFailure
from shellingham import detect_shell


@contextmanager
def spawn_shell(command, cwd: Optional[Union[Path, str]] = None) -> spawn:
    try:
        name, path = detect_shell(os.getpid())
    except (RuntimeError, ShellDetectionFailure):
        shell = None

        if os.name == "posix":
            shell = os.environ.get("SHELL")
        elif os.name == "nt":
            shell = os.environ.get("COMSPEC")

        if not shell:
            raise RuntimeError("Unable to detect the current shell.")

        name, path = Path(shell).stem, shell

    c = pexpect.spawn(path, args=["-i"])
    c.sendline(command)
    if cwd:
        c.sendline(f"cd {cwd}")
    c.interact(escape_character=None)
    yield c

    sys.exit(c.exitstatus)
