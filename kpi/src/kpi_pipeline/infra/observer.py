import os
import warnings
from contextlib import contextmanager

import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

import kpi_pipeline.infra.exceptions as exceptions
from kpi_pipeline.base.protocols import ObserverProtocol

load_dotenv()

DEFAULT_IGNORE_ERRORS: tuple[type[Exception], ...] = (
    exceptions.DatasetAccessError,
    exceptions.EmptyDataArrayError,
    exceptions.NoDownloadedDataError,
)


class DebuggingObserver(ObserverProtocol):
    def __init__(
        self,
        skip_on_error: bool = False,
        ignore_errors: tuple[type[Exception], ...] | None = None,
        break_on_var: str | None = None,
        allow_error_on_var: str | None = None,
        project_name_short: str | None = None,
        suppress_nan_warnings: bool = True,
    ):
        if ignore_errors is None:
            ignore_errors = DEFAULT_IGNORE_ERRORS
        self.ignore_errors = ignore_errors
        self.skip_on_error = skip_on_error

        self.break_on_var = break_on_var
        self.allow_error_on_var = allow_error_on_var
        self.project_name_short = project_name_short
        self._var: str | None = None
        self._scope: str | None = None

        if suppress_nan_warnings:
            warnings.filterwarnings(
                "ignore",
                category=RuntimeWarning,
                message=".*All-NaN slice encountered.*",
            )

    @contextmanager
    def with_scope(self, *, scope: str | None = None):
        if scope is not None:
            self._scope = scope
        try:
            yield
        finally:
            self._scope = None

    @contextmanager
    def with_project(self, *, project_name_short: str):
        self.project_name_short = project_name_short
        self.log(message=f"Starting project {project_name_short}")
        try:
            yield
        finally:
            self.project_name_short = None

    @contextmanager
    def watch(self, *, var: str | None = None):
        if var is not None:
            self._var = var
            self._check_field()
        try:
            yield
        except tuple(self.ignore_errors):
            pass
        except Exception as e:
            self._on_error(error=e)
        finally:
            self._var = None

    def _check_field(self):
        if self.break_on_var is not None and self._var == self.break_on_var:
            breakpoint()

    def _error_allowed(self) -> bool:
        if self.allow_error_on_var is not None:
            return self._var == self.allow_error_on_var
        return False

    def _on_error(self, *, error):
        if self.skip_on_error and not self._error_allowed():
            if self._var:
                var_str = f".{self._var}"
            else:
                var_str = ""
            if self.project_name_short:
                project_str = f"   project: {self.project_name_short}"
            else:
                project_str = ""
            if self._scope or self._var or self.project_name_short:
                print(f" --- {self._scope}{var_str}{project_str} ---")
            print(f"Warning: {error}\n")
        else:
            raise

    def log(self, *, message: str):
        print(f"----- {message} -----")


class SentryObserver(ObserverProtocol):
    def __init__(
        self, ignore_errors: tuple[type[Exception], ...] = DEFAULT_IGNORE_ERRORS
    ):
        self.ignore_errors = ignore_errors
        # initialize sentry sdk
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            send_default_pii=True,
            integrations=[AwsLambdaIntegration(timeout_warning=True)],
            ignore_errors=self.ignore_errors,
        )

    @contextmanager
    def with_scope(self, *, scope: str | None = None):
        with sentry_sdk.new_scope() as _scope:
            if scope is not None:
                _scope.set_tag("scope", scope)
            yield

    @contextmanager
    def with_project(self, *, project_name_short: str):
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("project_name_short", project_name_short)
            yield

    @contextmanager
    def watch(self, *, var: str | None = None):
        with sentry_sdk.new_scope() as scope:
            if var is not None:
                scope.set_tag("var", var)
            try:
                yield
            except Exception as e:
                self._on_error(error=e)

    def _on_error(self, *, error: Exception) -> None:
        sentry_sdk.capture_exception(error, level="warning")

    def log(self, *, message: str):
        sentry_sdk.capture_message(message, level="info")
