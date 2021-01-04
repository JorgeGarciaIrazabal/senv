import os
import signal
import sys
from contextlib import contextmanager
from os import environ

import pexpect
from clikit.utils.terminal import Terminal
from poetry.utils.shell import Shell

from pysenv.log import log

WINDOWS = sys.platform == "win32"


@contextmanager
def temp_environ():
    environ = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(environ)


class PysenvShell(Shell):
    def activate(self, command):
        if environ.get("PYSENV_ACTIVE", "0") == "1":
            log.info("environment already active")
        environ["PYSENV_ACTIVE"] = "1"
        terminal = Terminal()
        with temp_environ():
            c = pexpect.spawn(
                self._path, ["-i"], dimensions=(terminal.height, terminal.width)
            )

        if self._name == "zsh":
            c.setecho(False)

        c.sendline(command)

        def resize(sig, data):
            terminal = Terminal()
            c.setwinsize(terminal.height, terminal.width)

        signal.signal(signal.SIGWINCH, resize)

        # Interact with the new shell.
        c.interact(escape_character=None)
        c.close()
        environ.pop("PYSENV_ACTIVE")
        sys.exit(c.exitstatus)


if __name__ == "__main__":
    environ["PYSENV_ACTIVE"] = "1"
    PysenvShell.get().activate(command="conda activate pysenv_example")
    environ.pop("PYSENV_ACTIVE")
