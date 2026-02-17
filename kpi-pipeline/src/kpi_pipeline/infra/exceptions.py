class DatasetAccessError(Exception):
    """Raised when a specific variable is missing from the dataset."""

    pass


class EmptyDataArrayError(Exception):
    """Raised when a data array is empty."""

    pass


class NoDownloadedDataError(Exception):
    """Raised when no data is found from the database."""

    pass


class DataTypeCastingError(Exception):
    """Raised when a data array cannot be cast to the specified data type."""

    pass


class ValidationError(Exception):
    """Raised when explicit validation fails."""

    pass
