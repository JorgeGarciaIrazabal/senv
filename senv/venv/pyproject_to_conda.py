#!/usr/bin/env python
import collections
import re
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

import jinja2
import yaml
from conda_lock.src_parser import LockSpecification
from conda_lock.src_parser.pyproject_toml import (
    normalize_pypi_name,
    parse_poetry_pyproject_toml,
    poetry_version_to_conda_version,
    to_match_spec,
)

from senv.errors import SenvInvalidPythonVersion
from senv.log import log
from senv.settings.config import Config

template = """
package:
  name: {{ name }}
  version: "{{ version }}"

source:
  path: {{ src_path }}

build:
  noarch: python
  script:
    - python -m pip install --no-deps --ignore-installed -vv .

requirements:
  host:
    - {{ python_version }}
    - pip
  run:
{%- for run_dep in run_deps %}
    - {{ run_dep }}
{%- endfor %}

about:
{% if home_url != '__NONE__' %}
  home: {{ home_url }}
{% endif %}
  license: Apache-2.0
"""

version_pattern = re.compile("version='(.*)'")


def yaml_safe_dump(yaml_dict: Dict, path: Path):
    s = StringIO()
    yaml.safe_dump(yaml_dict, s)
    # need to add `---` to the yaml to fix some issues with conda-build
    # https://github.com/conda/conda-build/issues/3860#issuecomment-740769768
    yaml_str = f"---\n{s.getvalue()}"
    path.write_text(yaml_str)


def _conda_spec_to_conda_build_req(req: str):
    if "[" in req:
        pkg_name, _, specifier = req.partition("[")
        version_match = re.search(version_pattern, specifier)
        assert version_match, req
        version = version_match.group(1)
        return f"{pkg_name} {version}"
    else:
        return req


def _populate_python_version(python_version, dependencies):
    python_req = [r for r in dependencies if r.split()[0] == "python"]
    if len(python_req) == 1:
        if python_version is not None and python_version != python_req[0]:
            log.warn(
                "Python version in the pyproject.toml is different than the one provided"
            )
        elif python_version is None:
            python_version = python_req[0]
    elif python_version is None:
        raise SenvInvalidPythonVersion(
            "No python version provided or defined in pyproject.toml"
        )
    return python_version


# TODO: probably make a Pull request in conda lock to make this logic more accessible
def _parse_pyproject_toml(
    platform: str, include_dev_dependencies: bool
) -> LockSpecification:
    specs: List[str] = []
    deps = Config.get().dependencies
    if include_dev_dependencies:
        deps.update(Config.get().dev_dependencies)

    for depname, depattrs in deps.items():
        conda_dep_name = normalize_pypi_name(depname)
        if isinstance(depattrs, collections.Mapping):
            poetry_version_spec = depattrs["version"]
            # TODO: support additional features such as markers for things like sys_platform, platform_system
        elif isinstance(depattrs, str):
            poetry_version_spec = depattrs
        else:
            raise TypeError(f"Unsupported type for dependency: {depname}: {depattrs:r}")
        conda_version = poetry_version_to_conda_version(poetry_version_spec)
        spec = to_match_spec(conda_dep_name, conda_version)

        if conda_dep_name == "python":
            specs.insert(0, spec)
        else:
            specs.append(spec)

    return LockSpecification(
        specs=specs, channels=Config.get().senv.conda_channels, platform=platform
    )


def _get_dependencies_from_pyproject(include_dev_dependencies):
    lock_spec = parse_poetry_pyproject_toml(
        Config.get().config_path,
        platform="linux-64",
        include_dev_dependencies=include_dev_dependencies,
    )
    dependencies = [_conda_spec_to_conda_build_req(spec) for spec in lock_spec.specs]
    return dependencies


def pyproject_to_recipe_yaml(
    python_version: Optional[str] = None,
    output: Path = Path("conda.recipe") / "meta.yaml",
):
    output_dict = pyproject_to_recipe_dict(python_version)

    recipe_dir = output.parent
    recipe_dir.mkdir(parents=True, exist_ok=True)
    yaml_safe_dump(output_dict, output)


def pyproject_to_recipe_dict(python_version: Optional[str] = None) -> Dict:
    dependencies = _get_dependencies_from_pyproject(include_dev_dependencies=False)
    python_version = _populate_python_version(python_version, dependencies)
    if python_version != Config.get().python_version:
        log.warn(
            "Python version in the pyproject.toml is different than the one provided"
        )
    if python_version is None:
        raise SenvInvalidPythonVersion(
            f"No python version provided or defined in {Config.get().config_path}"
        )
    output = jinja2.Template(template).render(
        name=Config.get().package_name,
        version=Config.get().version,
        run_deps=dependencies,
        src_path=str(Config.get().config_path),
        python_version=python_version,
        home_url=Config.get().homepage,
    )
    return yaml.safe_load(output)


def pyproject_to_conda_venv_dict() -> Dict:
    channels = Config.get().senv.conda_channels
    dependencies = _get_dependencies_from_pyproject(include_dev_dependencies=True)

    return dict(
        name=Config.get().venv_name, channels=channels, dependencies=dependencies
    )
