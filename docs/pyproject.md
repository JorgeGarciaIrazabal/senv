# pyproject.toml

Senv allows to configure your virtual environment and your publishing configuration through the `pyproject.toml` file

Bellow are described all the properties you can configure in this file.

## configuration

| namespace | name | type | default | description |
|-----|-----|-----|-----|-----|
| tool.senv | build-system | Enum Choices {conda, poetry} |  | Default system used to build the virtual environment and the package |
| tool.senv | name | <class 'str'> |  | The name of the package |
| tool.senv | version | <class 'str'> |  | The version of the package |
| tool.senv | description | <class 'str'> |  | A short description of the package |
| tool.senv | license | <class 'str'> | Proprietary | License of the package. License identifiers are listed at [SPDX](https://spdx.org/licenses/) |
| tool.senv | authors | typing.List[str] |  | The authors of the package. Authors must be in the form `name <email>` |
| tool.senv | readme | <class 'str'> |  | (Poetry only) The readme file of the package. The file can be either `README.rst` or `README.md` |
| tool.senv | homepage | <class 'str'> |  | An URL to the website of the project |
| tool.senv | repository | <class 'str'> |  | An URL to the repository of the project |
| tool.senv | documentation | <class 'str'> |  | An URL to the documentation of the project |
| tool.senv | keywords | typing.List[str] |  | (Poetry only) A list of keywords (max: 5) that the package is related to |
| tool.senv | classifiers | typing.List[str] |  | (Poetry only) A list of PyPI [trove classifiers](https://pypi.org/classifiers/) that describe the project |
| tool.senv | packages | typing.Dict[str, str] |  | (Poetry Only) A list of packages and modules to include in the final distribution |
| tool.senv | dependencies | typing.Dict[str, typing.Any] |  | List of dependencies to be included in the final package and in the virtual environment |
| tool.senv | dev-dependencies | typing.Dict[str, typing.Any] |  | List of dependencies to be included in the virtual environment but not in the final package |
| tool.senv | scripts | typing.Dict[str, str] |  | The scripts or executables that will be installed when installing the package |
| tool.senv | conda-channels | typing.List[str] |  | (Conda Only) The conda channels to build the package and the virtual environment |
| tool.senv | conda-path | <class 'pathlib.Path'> |  | (Conda Only) path of the conda executable. (If not defined, it will try to find it in PATH) |
| tool.senv | poetry-path | <class 'pathlib.Path'> |  | (Poetry Only) path of the poetry executable. (If not defined, it will try to find it in PATH) |
| tool.senv.env | build-system | Enum Choices {conda, poetry} |  | Default system used to build the virtual environment. (If not defined, use tool.senv.build_system) |
| tool.senv.env | conda-lock-platforms | typing.Set[str] | {'osx-64', 'linux-64', 'win-64'} | (Conda only) Default set of platforms to solve and lock the dependencies for |
| tool.senv.env | conda-lock-path | <class 'pathlib.Path'> | conda_env.lock.json | (Conda only) The path of where the lock file will be generated |
| tool.senv.env | name | <class 'str'> |  | (Conda only) Alternative name for the conda environment (by default: tool.senv.name) |
| tool.senv.package | build-system | Enum Choices {conda, poetry} |  | Default system used to build the final package. (If not defined, use tool.senv.build_system) |
| tool.senv.package | conda-build-path | <class 'pathlib.Path'> |  |  |
| tool.senv.package | conda-publish-channel | <class 'str'> |  |  |
| tool.senv.package | conda-lock-path | <class 'pathlib.Path'> | package_locked.lock.json |  |
| tool.senv.package | poetry-publish-repository | <class 'str'> |  |  |
