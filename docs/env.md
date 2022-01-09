# env command

The env command manages the creation and management of one or multiple virtual environments for development or ci.

## Create virtual environment

#### Create your default virtual environment

By default, senv will use `conda` as your build system, and the channel `conda-forge`. By running

<div class="termy">

```console
$ senv env install
generating lock files
---> 100%
installing dependencies with conda
---> 100%
Dependencies successfully installed
```

</div>

A new virtual environment with your project's name, was created along with the windows, macos, and linux lock files in the `env_locks_dir`.

This can be configured in the pyproject.toml file, [see configure sections](#Configure your virtual environments)


#### Create a poetry environment along with the conda environment

<div class="termy">

```console
$ senv env install --build-system poetry
generating lock file
---> 100%
installing dependencies with poetry
---> 100%
Dependencies successfully installed
```

</div>

in this case, a poetry environment and a poetry.lock file was created

## Activate your environment

You can activate your environment by simply running

<div class="termy">

```console
$ senv env shell
env activate
```

</div>

Or activate using poetry with 

<div class="termy">

```console
$ senv env shell --build-system poetry
env activate
```

</div>

This flexibility can potentially be useful if you are planning to distribute you package with **pypi and conda** and you want to test both cases in CI.


## Update your environment

If you want to update your dependencies (based on the constraints defined in pyproject.toml), you can run the `update` command

<div class="termy">

```console
$ senv env update
generating lock file
---> 100%
installing dependencies with conda
---> 100%
Dependencies successfully installed
```

</div>

or update both multiple build-systems at the same time

<div class="termy">


```console
$ senv env update --build-system conda --build-system poetry
generating conda lock files
---> 100%
installing dependencies with conda
---> 100%
generating poetry lock file
---> 100%
installing dependencies with poetry
---> 100%
Environment susccessfully updated
```

</div>

## Lock your environment

To just update the lock files without updating your environment, use `lock`

<div class="termy">

```console
// you can also include mulple --build-system like in the command `update`
$ senv env lock
generating lock file
---> 100%
Dependencies successfully installed
```

</div>


## Configure your virtual environments


# Full CLI documentation

::: mkdocs-click
    :module: senv.main
    :command: env_command
