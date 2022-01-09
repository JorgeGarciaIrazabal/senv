# Project in a very early stage
There are a lot of features missing and documentation might not align with the tool. 

# senv (Super Environment)

**Senv (Super Environment)** is a tool to simplify **dependency management**, **packaging**, **distribution**, **testing**, and **consumption** of your applications and libraries.

Full documentation [here](https://jorgegarciairazabal.github.io/senv/)

## Why Not Poetry?
Poetry and pyproject are amazing, it seems to cover most of the cases, but we think 
there are few reasons why **senv** could improve your development experience.

1. **Unify the package and environment definition**
   
   Poetry does a great job unifying the definition of your package release
   and the dev environment, but it doesn't integrate very well with conda.
   Senv also allows you to define you package and dev environment
   with pyproject.toml using the conda solver (if desired)

2. **One configuration/one cli -> multiple build systems**
   
   With senv, you can create dev environments, build, and publish your packages with poetry and/or conda.

   It also integrates with conda-lock to maintain the dev experience with the same cli. (senv likes lock files)

3. **New ways to consume your package**

   New tools like pipx and condax expanded how people consume python packages. As they both create isolated environments, 
   your clis can now be published with a pinned set of dependencies preventing unexpected problems with 
   untested dependency versions. Using `senv package publish --locked` will publish your package 
   with the exact dependencies that was tested, and it is smart enough to exclude the `dev-dependencies`


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
$ senvx install senv-locked
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
# Default build system [conda, poetry]: $ conda

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

Senv also works using **tool.poetry.{any_key}** so plugins like [poetry-dynamic-versioning](https://pypi.org/project/poetry-dynamic-versioning/) work using senv.

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

Learn more about the [env](docs/env.md), [config](docs/config.md), and [package](docs/package.md) commands
