#!/usr/bin/env python

import tomlkit
import jinja2
from pathlib import Path
import re
from typing import Dict, Optional

import yaml
from conda_lock.common import get_in
from conda_lock.src_parser.pyproject_toml import parse_poetry_pyproject_toml

from ..log import log
from ..errors import PysenvInvalidPythonVersion

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
    - poetry
  run:
{%- for run_dep in run_deps %}
    - {{ run_dep }}
{%- endfor %}

about:
  home: {{ home_url|default('https://git.the.flatiron.com/data-platforms') }}
  license: INTERNAL
"""

version_pattern = re.compile("version='(.*)'")


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
        raise PysenvInvalidPythonVersion(
            "No python version provided or defined in pyproject.toml"
        )
    return python_version


def _get_dependencies_from_pyproject(pyproject_path, include_dev_dependencies):
    lock_spec = parse_poetry_pyproject_toml(
        pyproject_path,
        platform="linux-64",
        include_dev_dependencies=include_dev_dependencies,
    )
    dependencies = [_conda_spec_to_conda_build_req(spec) for spec in lock_spec.specs]
    return dependencies


def pyproject_to_recipe_yaml(
    pyproject_path: Path, python_version: Optional[str] = None
):
    output = pyproject_to_recipe_dict(pyproject_path, python_version)

    recipe_dir = Path("conda.recipe")
    recipe_dir.mkdir(parents=True, exist_ok=True)
    yaml.dump(output, (recipe_dir / "meta.yaml").open(mode="w"))


def pyproject_to_recipe_dict(
    pyproject_path: Path, python_version: Optional[str] = None
) -> Dict:
    data = tomlkit.loads(pyproject_path.read_text())
    tool_poetry_dict = data["tool"]["poetry"]
    package_name = tool_poetry_dict["name"]
    version = tool_poetry_dict["version"]
    dependencies = _get_dependencies_from_pyproject(pyproject_path, False)
    python_version = _populate_python_version(python_version, dependencies)
    output = jinja2.Template(template).render(
        name=package_name,
        version=version,
        run_deps=dependencies,
        src_path=str(pyproject_path.parent.resolve()),
        python_version=python_version,
        home_url=tool_poetry_dict.get("homepage"),
    )
    return yaml.safe_load(output)


def pyproject_to_env_dict(
    pyproject_path: Path
) -> Dict:
    data = tomlkit.loads(pyproject_path.read_text())
    tool_poetry_dict = data["tool"]["poetry"]
    channels = get_in(["tool", "conda-lock", "channels"], data, [])
    package_name = tool_poetry_dict["name"]
    dependencies = _get_dependencies_from_pyproject(pyproject_path, True)

    return dict(
        name=package_name,
        channels=channels,
        dependencies=dependencies
    )
