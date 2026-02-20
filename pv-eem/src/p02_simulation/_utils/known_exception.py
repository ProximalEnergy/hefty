from enum import Enum


class KnownExceptionType(Enum):
    """Known excpetion start with 2xx because they are expected
    and are not errors
    """

    # Missing data from database
    NO_IRRADIANCE = 211
    NO_AMBIENT_TEMPERATURE = 212
    NO_SOILING = 213

    # Expected errors from poai section of the model
    GTI_DIRINT_NON_CONVERGENCE = 224

    # Exports
    NO_EXPORT_TRANSFORMER = 231


class KnownException(Exception):
    """Known exceptions that can happen in a performance model that we don't want
    to worry about and therefore will skip notifications for
    """

    def __init__(self, error_type: KnownExceptionType, message: str):
        self.error_type = error_type
        self.message = message

    def __str__(self):
        return f"KnownException: {self.error_type}, {self.message}"
