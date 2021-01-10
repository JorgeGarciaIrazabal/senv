class SenvError(Exception):
    pass


class SenvInvalidPythonVersion(SenvError):
    pass


class SenvNotSupportedPlatform(SenvError):
    pass
