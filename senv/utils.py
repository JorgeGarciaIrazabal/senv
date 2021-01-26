import contextlib
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator
from unittest.mock import patch

from conda import iteritems
from conda.core.solve import Resolve
from conda.exports import MatchSpec

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
def mock_conda_resolver():
    def new_version_solver(self, C, specs, include0=False):
        # each of these are weights saying how well packages match the specs
        #    format for each: a C.minimize() objective: Dict[varname, coeff]
        eqc = {}  # channel
        eqv = {}  # version
        eqb = {}  # build number
        eqa = {}  # arch/noarch
        eqt = {}  # timestamp

        sdict = {}  # Dict[package_name, PackageRecord]

        for s in specs:
            s = MatchSpec(s)  # needed for testing
            sdict.setdefault(s.name, [])
            # # TODO: this block is important! can't leave it commented out
            # rec = sdict.setdefault(s.name, [])
            # if s.target:
            #     dist = Dist(s.target)
            #     if dist in self.index:
            #         if self.index[dist].get('priority', 0) < MAX_CHANNEL_PRIORITY:
            #             rec.append(dist)

        for name, targets in iteritems(sdict):
            pkgs = reversed(
                [(self.version_key(p), p) for p in self.groups.get(name, [])]
            )
            pkey = None
            # keep in mind that pkgs is already sorted according to version_key (a tuple,
            #    so composite sort key).  Later entries in the list are, by definition,
            #    greater in some way, so simply comparing with != suffices.
            for version_key, prec in pkgs:
                if targets and any(prec == t for t in targets):
                    continue
                if pkey is None:
                    ic = iv = ib = it = ia = 0
                # valid package, channel priority
                elif pkey[0] != version_key[0] or pkey[1] != version_key[1]:
                    ic += 1
                    iv = ib = it = ia = 0
                # version
                elif pkey[2] != version_key[2]:
                    iv += 1
                    ib = it = ia = 0
                # build number
                elif pkey[3] != version_key[3]:
                    ib += 1
                    it = ia = 0
                # arch/noarch
                elif pkey[4] != version_key[4]:
                    ia += 1
                    it = 0
                elif not self._solver_ignore_timestamps and pkey[5] != version_key[5]:
                    it += 1

                prec_sat_name = self.to_sat_name(prec)
                if ic or include0:
                    eqc[prec_sat_name] = ic
                if iv or include0:
                    eqv[prec_sat_name] = iv
                if ib or include0:
                    eqb[prec_sat_name] = ib
                if ia or include0:
                    eqa[prec_sat_name] = ia
                if it or include0:
                    eqt[prec_sat_name] = it
                pkey = version_key

        return eqc, eqv, eqb, eqa, eqt

    with patch.object(Resolve, "generate_version_metrics", autospec=True) as m:
        m.side_effect = new_version_solver
        yield m
