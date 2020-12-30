class PysenvError(Exception):
    pass


class PysenvInvalidPythonVersion(PysenvError):
    pass


class PysenvNotSupportedPlatform(PysenvError):
    pass
