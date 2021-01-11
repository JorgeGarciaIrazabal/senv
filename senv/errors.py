class SenvError(Exception):
    pass


class SenvInvalidPythonVersion(SenvError):
    pass


class SenvNotSupportedPlatform(SenvError):
    pass


class SenvBadConfiguration(SenvError):
    pass
