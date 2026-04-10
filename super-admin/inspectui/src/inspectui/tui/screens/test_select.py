"""Test selection screen."""

import curses
from datetime import datetime
from typing import TYPE_CHECKING, Any

from inspectui.core.models import (
    ProjectInfo,
    TestResult,
    TestRunSummary,
    TestStatus,
)
from inspectui.core.tests import TestRegistry, TestRunner
from inspectui.core.tests.base import BaseTest
from inspectui.core.tests.params_config import get_shared_test_params
from inspectui.tui.colors import PAIR_HEADER, PAIR_WARNING
from inspectui.tui.components.list_selector import ListSelector
from inspectui.tui.screens.base import BaseScreen
from inspectui.tui.screens.test_results import TestResultsScreen

if TYPE_CHECKING:
    from inspectui.tui.app import InspectUIApp


class TestSelectScreen(BaseScreen):
    """Screen for selecting and running tests."""

    def __init__(self, app: "InspectUIApp") -> None:
        super().__init__(app)
        self.tests: list[type[BaseTest]] = TestRegistry.get_all_tests()
        self.selector: ListSelector[type[BaseTest]] | None = None

        if self.tests:
            self.selector = ListSelector(
                self.stdscr,
                self.tests,
                get_display=self._get_test_display,
                multi_select=True,
                title="Select Tests to Run",
                start_y=2,
            )

    def _get_test_display(self, test_class: type[BaseTest]) -> str:
        """Get display string for a test."""
        return f"{test_class.name}: {test_class.description}"

    def render(self) -> None:
        """Render the test selection screen."""
        self.clear()
        height, width = self.get_dimensions()

        active = self.app.get_active_project_names()
        self.stdscr.attron(curses.color_pair(PAIR_HEADER))
        if active:
            header = f"Active projects: {len(active)}"
        else:
            header = "No active projects selected"
        self.stdscr.addstr(0, 0, header[: width - 1])
        self.stdscr.attroff(curses.color_pair(PAIR_HEADER))

        if not self.tests:
            msg = "No tests available"
            self.stdscr.addstr(height // 2, max(0, (width - len(msg)) // 2), msg)
            self.stdscr.addstr(height // 2 + 2, 2, "Press q to go back")
            self.refresh()
            return

        if self.selector:
            self.selector.render()

        help_text = "a: select all | n: select none | r: run all"
        self.stdscr.addstr(1, 0, help_text[: width - 1])

        status = (
            f"{len(self.tests)} tests | Space: toggle, Enter: run selected, q: back"
        )
        self.draw_status_bar(status)
        self.refresh()

    def handle_input(self, key: int) -> None:
        """Handle keyboard input."""
        if not self.selector:
            if key == ord("q"):
                self._go_back()
            return

        if key == ord("a"):
            self.selector.selected_indices = set(range(len(self.tests)))
            return

        if key == ord("n"):
            self.selector.selected_indices = set()
            return

        if key == ord("r"):
            self._run_tests(test_classes=self.tests)
            return

        should_continue, selected = self.selector.handle_input(key)

        if not should_continue:
            if selected and len(selected) > 0:
                self._run_tests(test_classes=selected)
            else:
                self._go_back()

    def _configure_test(self, *, test_class: type[BaseTest]) -> BaseTest:
        """Create a test instance using shared ``test_params`` and user config."""
        test = test_class()
        if not test.has_parameters():
            return test

        saved = self._get_saved_params(test_name=test_class.name)
        for param in test_class.parameters:
            if param.name in saved:
                test.set_param(param.name, saved[param.name])
            else:
                test.set_param(param.name, param.default)

        return test

    def _run_tests(self, *, test_classes: list[type[BaseTest]]) -> None:
        """Run the selected tests using ``test_params`` and user config."""
        if not self.app.cache_manager or not self.app.data_fetcher:
            return

        test_configs: list[tuple[type[BaseTest], dict[str, Any]]] = []
        for test_class in test_classes:
            test = self._configure_test(test_class=test_class)
            test_configs.append((test_class, test.get_param_values()))

        active_projects, missing = self.app.get_active_projects()
        if not active_projects:
            self._show_message(message="No active projects selected.")
            return

        results: list[TestResult] = []
        passed = failed = skipped = errors = 0

        for name in missing:
            results.append(
                TestResult(
                    test_name="project_missing",
                    project_name=name,
                    passed=False,
                    message="Project not found",
                    status=TestStatus.ERROR,
                )
            )
            errors += 1

        total_projects = len(active_projects)
        for idx, project in enumerate(active_projects, start=1):
            self._show_progress(
                project_name=project.name_short,
                idx=idx,
                total=total_projects,
            )
            ok = self._load_project_data(project=project)
            if not ok:
                results.append(
                    TestResult(
                        test_name="project_load",
                        project_name=project.name_short,
                        passed=False,
                        message="Failed to load project data",
                        status=TestStatus.ERROR,
                    )
                )
                errors += 1
                continue

            tests = self._build_tests_from_configs(configs=test_configs)
            runner = TestRunner(self.app.cache_manager)
            summary = runner.run_test_instances(
                tests=tests,
                project_name=project.name_short,
            )
            results.extend(summary.results)
            passed += summary.passed
            failed += summary.failed
            skipped += summary.skipped
            errors += summary.errors

        summary = TestRunSummary(
            total=len(results),
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            results=results,
            recorded_at=datetime.now(),
        )

        if self.app.cache_manager:
            self.app.cache_manager.save_last_test_run(summary=summary)

        self.app.switch_screen(TestResultsScreen(self.app, summary))

    def _build_tests_from_configs(
        self,
        *,
        configs: list[tuple[type[BaseTest], dict[str, Any]]],
    ) -> list[BaseTest]:
        """Build test instances from saved parameter configs."""
        instances: list[BaseTest] = []
        for test_class, params in configs:
            test = test_class()
            for name, value in params.items():
                test.set_param(name, value)
            instances.append(test)
        return instances

    def _get_saved_params(self, *, test_name: str) -> dict[str, Any]:
        """Return params from ``test_params.py`` merged with optional user config."""
        shared_params = get_shared_test_params(test_name=test_name)
        user_params = self._get_user_saved_params(test_name=test_name)

        resolved_params = shared_params.copy()
        resolved_params.update(user_params)
        return resolved_params

    def _get_user_saved_params(self, *, test_name: str) -> dict[str, Any]:
        """Return user-saved params from home config."""
        if not self.app.config_manager:
            return {}
        params = self.app.config_manager.get(f"test_params.{test_name}", {})
        if isinstance(params, dict):
            return params
        return {}

    def _load_project_data(self, *, project: ProjectInfo) -> bool:
        """Load project data from cache or database."""
        if not self.app.cache_manager or not self.app.data_fetcher:
            return False

        cache_manager = self.app.cache_manager
        try:
            if cache_manager.has_valid_cache(project.name_short):
                if cache_manager.load_from_disk(project.name_short):
                    return True

            devices = self.app.data_fetcher.fetch_devices(project.name_short)
            tags = self.app.data_fetcher.fetch_tags(project.name_short)
            cache_manager.set_project(project, devices, tags)
            return True
        except Exception:
            return False

    def _show_progress(
        self,
        *,
        project_name: str,
        idx: int,
        total: int,
    ) -> None:
        """Show progress message while running tests."""
        self.clear()
        height, width = self.get_dimensions()
        msg = f"Running tests for {project_name} ({idx}/{total})..."
        self.stdscr.addstr(height // 2, max(0, (width - len(msg)) // 2), msg)
        self.refresh()

    def _show_message(self, *, message: str) -> None:
        """Show a message and wait for a key press."""
        self.clear()
        height, width = self.get_dimensions()
        self.stdscr.attron(curses.color_pair(PAIR_WARNING))
        self.stdscr.addstr(height // 2, 2, message[: width - 4])
        self.stdscr.attroff(curses.color_pair(PAIR_WARNING))
        self.stdscr.addstr(height - 2, 2, "Press any key to continue...")
        self.refresh()
        if self.stdscr:
            self.stdscr.getch()

    def _go_back(self) -> None:
        """Return to the main menu."""
        from inspectui.tui.screens.main_menu import MainMenuScreen  # noqa: PLC0415

        self.app.switch_screen(MainMenuScreen(self.app))
