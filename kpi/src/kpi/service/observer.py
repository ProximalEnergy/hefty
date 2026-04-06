import logging
import warnings
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from types import TracebackType
from warnings import WarningMessage

import sentry_sdk
from kpi.base.exception import (
    DatasetAccessError,
    KpiError,
    MissingDataError,
    NoDownloadedDataError,
)
from kpi.base.protocol import ObserverProtocol
from kpi.base.warning import KpiWarning

_log = logging.getLogger(__name__)


class NoOpObserver:
    """Observer that does standard python behavior."""

    def handle_error(self, error: Exception, *, field_name: str | None = None) -> None:
        _ = field_name
        raise error from error

    def handle_warnings(
        self,
        warning_messages: list[WarningMessage],
        *,
        field_name: str | None = None,
    ) -> None:
        _ = field_name
        for msg in warning_messages:
            warnings.showwarning(msg.message, msg.category, msg.filename, msg.lineno)


class LocalObserver:
    """Meant to skip errors and filter warnings to the console."""

    def __init__(
        self,
        *,
        ignore_errors: tuple[type[Exception], ...] | None = None,
        capture_warnings: tuple[type[Warning], ...] | None = None,
    ) -> None:
        if ignore_errors is None:
            ignore_errors = (
                DatasetAccessError,
                MissingDataError,
                NoDownloadedDataError,
            )

        self.ignore_errors = ignore_errors

        if capture_warnings is None:
            capture_warnings = (KpiWarning,)

        self.capture_warnings = capture_warnings

    def handle_error(self, error: Exception, *, field_name: str | None = None) -> None:
        if isinstance(error, self.ignore_errors):
            return
        if field_name:
            _log.info(" Field: %s", field_name)
        _log.info("Error: %s", error)
        return

    def handle_warnings(
        self,
        warning_messages: list[WarningMessage],
        *,
        field_name: str | None = None,
    ) -> None:
        for msg in warning_messages:
            if issubclass(msg.category, self.capture_warnings):
                if field_name:
                    _log.info(" Field: %s", field_name)
                _log.info("Warning: %s", msg.message)
        return


class SentryObserver:
    """Works with sentry to capture unexpected errors and filtered warnings."""

    def __init__(
        self,
        *,
        ignore_errors: tuple[type[Exception], ...] | None = None,
        capture_warnings: tuple[type[Warning], ...] | None = None,
    ) -> None:
        if ignore_errors is None:
            ignore_errors = (KpiError,)

        self.ignore_errors = ignore_errors

        if capture_warnings is None:
            capture_warnings = (KpiWarning,)

        self.capture_warnings = capture_warnings

    def handle_error(self, error: Exception, *, field_name: str | None = None) -> None:
        if isinstance(error, self.ignore_errors):
            return
        sentry_sdk.capture_exception(
            error,
            extras={
                "field_name": field_name,
            },
        )
        # then the script continues as normal and the error is not re-raised
        return

    def handle_warnings(
        self,
        warning_messages: list[WarningMessage],
        *,
        field_name: str | None = None,
    ) -> None:
        # no need to print warnings to the console since this is running on a lambda
        for msg in warning_messages:
            if issubclass(msg.category, self.capture_warnings):
                sentry_sdk.capture_message(
                    str(msg.message),
                    level="warning",
                    extras={
                        "field_name": field_name,
                        "category": msg.category.__name__,
                        "filename": msg.filename,
                        "lineno": msg.lineno,
                    },
                )


# default global observer
_global_observer: ObserverProtocol = NoOpObserver()

# current observer context variable to allow user override
_current_observer = ContextVar[ObserverProtocol | None]("observer", default=None)


class use_observer[T: ObserverProtocol]:
    """Proper way to invoke a user override"""

    def __init__(self, observer: T) -> None:
        self.observer = observer

    def __enter__(self) -> T:
        self.token = _current_observer.set(self.observer)
        return self.observer

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        _current_observer.reset(self.token)


def get_observer() -> ObserverProtocol:
    return _current_observer.get() or _global_observer


def set_global_observer(observer: ObserverProtocol) -> None:
    global _global_observer
    _global_observer = observer


@contextmanager
def observe(field_name: str | None = None) -> Generator[None, None, None]:
    observer = get_observer()
    with warnings.catch_warnings(record=True) as caught:
        try:
            yield
        except Exception as e:
            observer.handle_error(e, field_name=field_name)
        finally:
            caught_snapshot = list(caught)
            observer.handle_warnings(caught_snapshot, field_name=field_name)
