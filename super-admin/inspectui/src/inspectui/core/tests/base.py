"""Base test class and test registry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from inspectui.core.models import TestResult, TestStatus

if TYPE_CHECKING:
    from inspectui.core.cache import CacheManager


@dataclass
class TestParameter:
    """Definition of a configurable test parameter."""

    name: str
    param_type: str  # "int", "str", "int_list", "str_list", "bool"
    description: str
    default: Any = None
    required: bool = True


class BaseTest(ABC):
    """Abstract base class for all tests."""

    name: str = ""
    description: str = ""
    category: str = "general"

    # Define configurable parameters for this test
    parameters: list[TestParameter] = []

    def __init__(self) -> None:
        """Initialize test with default parameter values."""
        self._param_values: dict[str, Any] = {}
        for param in self.parameters:
            self._param_values[param.name] = param.default

    def set_param(self, name: str, value: Any) -> None:
        """Set a parameter value.

        Args:
            name: Parameter name.
            value: Parameter value.
        """
        self._param_values[name] = value

    def get_param(self, name: str) -> Any:
        """Get a parameter value.

        Args:
            name: Parameter name.

        Returns:
            The parameter value.
        """
        return self._param_values.get(name)

    def has_parameters(self) -> bool:
        """Check if this test has configurable parameters."""
        return len(self.parameters) > 0

    def get_param_values(self) -> dict[str, Any]:
        """Get a copy of parameter values."""
        return self._param_values.copy()

    @abstractmethod
    def run_test(self, cache: "CacheManager") -> TestResult:
        """Run the test and return a result.

        Args:
            cache: The cache manager with project data.

        Returns:
            TestResult with the test outcome.
        """
        pass

    def run(self, cache: "CacheManager") -> TestResult:
        """Backward-compatible alias for test execution."""
        return self.run_test(cache)

    def skip(self, reason: str) -> TestResult:
        """Return a skipped result."""
        return TestResult(
            test_name=self.name,
            passed=False,
            message=reason,
            status=TestStatus.SKIPPED,
        )

    def error(self, message: str) -> TestResult:
        """Return an error result."""
        return TestResult(
            test_name=self.name,
            passed=False,
            message=message,
            status=TestStatus.ERROR,
        )


class TestRegistry:
    """Registry for managing available tests."""

    _tests: dict[str, type[BaseTest]] = {}

    @classmethod
    def register(cls, test_class: type[BaseTest]) -> type[BaseTest]:
        """Register a test class."""
        if test_class.name:
            cls._tests[test_class.name] = test_class
        return test_class

    @classmethod
    def get_all_tests(cls) -> list[type[BaseTest]]:
        """Get all registered test classes."""
        return list(cls._tests.values())

    @classmethod
    def get_test(cls, name: str) -> type[BaseTest] | None:
        """Get a test class by name."""
        return cls._tests.get(name)

    @classmethod
    def get_tests_by_category(cls, category: str) -> list[type[BaseTest]]:
        """Get all tests in a category."""
        return [t for t in cls._tests.values() if t.category == category]


def parse_param_value(value_str: str, param_type: str) -> Any:
    """Parse a string value into the appropriate type.

    Args:
        value_str: The string value from user input.
        param_type: The parameter type ("int", "str", "int_list", "str_list", "bool").

    Returns:
        The parsed value.

    Raises:
        ValueError: If the value cannot be parsed.
    """
    value_str = value_str.strip()

    if param_type == "int":
        return int(value_str)

    elif param_type == "str":
        return value_str

    elif param_type == "bool":
        return value_str.lower() in ("true", "yes", "1", "y")

    elif param_type == "int_list":
        if not value_str:
            return []
        # Accept comma-separated or space-separated
        parts = value_str.replace(",", " ").split()
        return [int(p.strip()) for p in parts if p.strip()]

    elif param_type == "str_list":
        if not value_str:
            return []
        parts = value_str.replace(",", " ").split()
        return [p.strip() for p in parts if p.strip()]

    else:
        return value_str
