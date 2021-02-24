# Welcome to Senv


**Senv (Super Environment)** is a tool to simplify **dependency management**, **packaging**, **distribution**, and **consumption** of your applications and libraries.

It tries to solve most of the problems solved by the amazing application [Poetry](https://python-poetry.org/),
but adding important features for modern packaging and distribution needs. Some of these needs are:

- Support for building **conda or poetry** environments with the same `pyproject.toml` file
- Publish libraries in pypi and/or conda repositories with just one command 
- Distribution of locked applications (Applications like [pipx](https://github.com/pipxproject/pipx) and [condax](https://pypi.org/project/condax/) will benefit from it)
- Totally hermetic appp installation process. 
  Use **senvx** (standalone executable) to install your application in systems where you don't have any control (no python, no docker, etc),
  **senvx** will temporarily install all required dependencies needed and create a hermetic working environment for your application.

## Installation
<div class="termy">

```console
$ pip install senv
---> 100%
Successfully installed senv
```

</div>

### or even better with senvx

<div class="termy">

```console
$ curl {senvx_url} --output senvx
$ ./senvx install senv-locked
---> 100%
Successfully installed senv
```

</div>



## Getting started
start creating a pyproject.toml file for your project. 
The `init` command will ask you simple questions about your project to get you starting

<div class="termy">

```console
$ senv init
// It prompts for the project's name
# Project's name [{project_dir_name}]: $ your_project
// (if conda is not found)
# Install conda [Y/n]: $ Y
// default build system
# Default build system [CONDA, poetry]: $ conda

---> 100%
pyproject.toml created
```

</div>


## Add dependencies and dev-dependencies to pyproject.toml

senv uses the same pyptoject.toml structure as [poetry](https://python-poetry.org/docs/pyproject/).

```toml
[tool.senv.dependencies]
python = ">3.7.0, <3.10.0"
typer = "^0.3.2"

[tool.senv.dev-dependencies]
pytest = "^6.2.1"

[tool.senv]
build-system = "conda"
```

It actually supports using **tool.poetry.{any_key}** and plugins like [poetry-dynamic-versioning](https://pypi.org/project/poetry-dynamic-versioning/) should work with senv too.

```toml
[tool.poetry.dependencies]
python = ">3.7.0, <3.10.0"
typer = "^0.3.2"

[tool.poetry.dev-dependencies]
pytest = "^6.2.1"

# specific senv keys should still be with the keyworkd `senv`
[tool.senv] 
build-system = "conda"
```

## Dev environment

Now we are ready to create our first dev environment. Using the conda build-system, it will generate the following lock files:

 - conda-linux-64.lock
 - conda-osx-64.lock
 - conda-win-64.lock

You can define this along with the conda channels and other things in the pyproject.toml files (You can find all the options in [pyproject](./pyproject.md#configuration) )

<div class="termy">

```console
$ senv env install
generating lockfile for win-64
generating lockfile for osx-64
generating lockfile for linux-64

syncing environment
---> 100%
activate your environment running `senv env shell`
```

</div>

Learn more about the [env](./env.md), [config](./config.md), and [package](./package.md) commands
