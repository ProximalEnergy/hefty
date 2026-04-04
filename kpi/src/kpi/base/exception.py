# Purpose: define explicit common errors that may want to be ignored
# for example, we don't need sentry notifying us every time time series data is missing.


class KpiError(Exception):
    """Any error explicitly raised by this package."""


class DatasetAccessError(KpiError):
    """Raised when a specific variable is missing from the dataset."""


class EmptyDataArrayError(KpiError):
    """Raised when a data array is empty."""


class NoDownloadedDataError(KpiError):
    """Raised when no data is found from the database."""


class DataTypeCastingError(KpiError):
    """Raised when a data array cannot be cast to the specified data type."""


class ValidationError(KpiError):
    """Raised when explicit validation fails."""
