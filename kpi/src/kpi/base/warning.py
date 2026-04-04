# Purpose: contrary to the exceptions, the purpose is to define explicit
# warnings that DO want to be captured
# For example, we don't want numpy mean of empty slice warnings to be reported to sentry
# but we may want to notify sentry of a particular validation warning.


class KpiWarning(Warning):
    """Any warning explicitly raised by this package."""


class ValidationWarning(KpiWarning):
    """Raised when a validation warning is encountered."""


class UnimplementedWarning(KpiWarning):
    """Raised when a unimplemented KPI is encountered."""
