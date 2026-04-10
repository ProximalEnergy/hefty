"""Execute ``BaseTest`` instances against a ``CacheManager`` and build summaries."""

from typing import TYPE_CHECKING

from inspectui.core.exception_messages import format_exception_message
from inspectui.core.models import TestResult, TestRunSummary, TestStatus
from inspectui.core.tests.base import BaseTest, TestRegistry

if TYPE_CHECKING:
    from inspectui.core.cache import CacheManager


class TestRunner:
    """Runs tests and collects results."""

    def __init__(self, cache: "CacheManager") -> None:
        """Initialize the test runner."""
        self.cache = cache

    def run_test_instance(
        self,
        *,
        test: BaseTest,
        project_name: str | None = None,
    ) -> TestResult:
        """Run a test instance (with parameters already configured).

        Args:
            test: The test instance to run.
            project_name: Optional project name to attach to results.

        Returns:
            The test result.
        """
        try:
            result = test.run(self.cache)
        except Exception as e:
            detail = format_exception_message(e)
            result = TestResult(
                test_name=test.name,
                passed=False,
                message=f"Test error: {detail}",
                status=TestStatus.ERROR,
            )
        if test.has_parameters():
            result.params = test.get_param_values()
        if project_name:
            result.project_name = project_name
        return result

    def run_test(
        self,
        *,
        test_class: type[BaseTest],
        project_name: str | None = None,
    ) -> TestResult:
        """Run a single test class (creates new instance with defaults).

        Args:
            test_class: The test class to run.
            project_name: Optional project name to attach to results.

        Returns:
            The test result.
        """
        test_instance = test_class()
        return self.run_test_instance(
            test=test_instance,
            project_name=project_name,
        )

    def run_test_instances(
        self,
        *,
        tests: list[BaseTest],
        project_name: str | None = None,
    ) -> TestRunSummary:
        """Run multiple test instances.

        Args:
            tests: List of test instances to run.
            project_name: Optional project name to attach to results.

        Returns:
            Summary of the test run.
        """
        results: list[TestResult] = []
        passed = 0
        failed = 0
        skipped = 0
        errors = 0

        for test in tests:
            result = self.run_test_instance(
                test=test,
                project_name=project_name,
            )
            results.append(result)

            if result.status == TestStatus.PASSED:
                passed += 1
            elif result.status == TestStatus.FAILED:
                failed += 1
            elif result.status == TestStatus.SKIPPED:
                skipped += 1
            elif result.status == TestStatus.ERROR:
                errors += 1

        return TestRunSummary(
            total=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            results=results,
        )

    def run_tests(
        self,
        *,
        test_classes: list[type[BaseTest]],
        project_name: str | None = None,
    ) -> TestRunSummary:
        """Run multiple test classes (creates new instances with defaults).

        Args:
            test_classes: List of test classes to run.
            project_name: Optional project name to attach to results.

        Returns:
            Summary of the test run.
        """
        instances = [cls() for cls in test_classes]
        return self.run_test_instances(
            tests=instances,
            project_name=project_name,
        )

    def run_all_tests(self, *, project_name: str | None = None) -> TestRunSummary:
        """Run all registered tests with default parameters."""
        test_classes = TestRegistry.get_all_tests()
        return self.run_tests(
            test_classes=test_classes,
            project_name=project_name,
        )
