"""Test results display screen."""

import curses
from enum import Enum
from typing import TYPE_CHECKING, Literal

from inspectui.core.models import TestResult, TestRunSummary, TestStatus
from inspectui.tui.colors import (
    PAIR_ERROR,
    PAIR_HEADER,
    PAIR_SUCCESS,
    PAIR_WARNING,
)
from inspectui.tui.screens.base import BaseScreen

if TYPE_CHECKING:
    from inspectui.tui.app import InspectUIApp


class ResultFilter(Enum):
    """Which test rows to show in the scrollable list."""

    ALL = "all"
    PASSING = "passing"
    FAILING = "failing"


# One scroll line: project header, test line, or condition line.
FlatRow = (
    tuple[Literal["project"], str, list[TestResult]]
    | tuple[Literal["test"], TestResult]
    | tuple[Literal["cond"], TestResult, int]
)


class TestResultsScreen(BaseScreen):
    """Screen for displaying test results."""

    def __init__(self, app: "InspectUIApp", summary: TestRunSummary) -> None:
        super().__init__(app)
        self.summary = summary
        self.scroll_offset = 0
        self._result_filter = ResultFilter.ALL
        self._show_conditions = True

    def _visible_results(self) -> list[TestResult]:
        """Results rows to show for the current filter (skipped only in All)."""
        rows = self.summary.results
        if self._result_filter == ResultFilter.ALL:
            return list(rows)
        if self._result_filter == ResultFilter.PASSING:
            return [r for r in rows if r.status == TestStatus.PASSED]
        return [r for r in rows if r.status in (TestStatus.FAILED, TestStatus.ERROR)]

    def _cycle_filter(self) -> None:
        """Rotate all → passing → failing → all."""
        order = (
            ResultFilter.ALL,
            ResultFilter.PASSING,
            ResultFilter.FAILING,
        )
        idx = order.index(self._result_filter)
        self._result_filter = order[(idx + 1) % len(order)]
        self._clamp_scroll()

    def _view_description(self) -> str:
        """Human-readable view mode for the header line."""
        rf = self._result_filter
        sc = self._show_conditions
        if rf == ResultFilter.ALL:
            return "all results" if sc else "all results (projects + tests only)"
        if rf == ResultFilter.PASSING:
            if sc:
                return "passing tests + passing conditions only"
            return "passing tests only"
        if sc:
            return "failed tests + failed conditions only"
        return "failed/error tests only"

    def _conditions_for_result(self, result: TestResult) -> list[dict[str, object]]:
        """Return condition sub-rows for the current filter.

        In **failing** view, only conditions with ``passed is False`` are shown
        (not passing ✓ lines under a failed test). In **passing** view, only
        ``passed is True``. **All** shows every condition.
        """
        raw = (result.details or {}).get("conditions")
        if not isinstance(raw, list):
            return []
        conds = [x for x in raw if isinstance(x, dict)]
        if self._result_filter == ResultFilter.FAILING:
            return [c for c in conds if c.get("passed") is False]
        if self._result_filter == ResultFilter.PASSING:
            return [c for c in conds if c.get("passed") is True]
        return conds

    @staticmethod
    def _contiguous_project_groups(
        visible: list[TestResult],
    ) -> list[tuple[str | None, list[TestResult]]]:
        """Split results into runs with the same ``project_name`` (order kept)."""
        if not visible:
            return []
        groups: list[tuple[str | None, list[TestResult]]] = []
        cur_key = visible[0].project_name
        cur: list[TestResult] = [visible[0]]
        for r in visible[1:]:
            if r.project_name == cur_key:
                cur.append(r)
            else:
                groups.append((cur_key, cur))
                cur_key = r.project_name
                cur = [r]
        groups.append((cur_key, cur))
        return groups

    def _project_group_color(self, *, group: list[TestResult]) -> int:
        """Color for the project header: red if any failure (test or condition)."""
        for r in group:
            if r.status in (TestStatus.FAILED, TestStatus.ERROR):
                return PAIR_ERROR
            raw = (r.details or {}).get("conditions")
            if not isinstance(raw, list):
                continue
            for c in raw:
                if isinstance(c, dict) and c.get("passed") is False:
                    return PAIR_ERROR
        if any(r.status == TestStatus.SKIPPED for r in group):
            return PAIR_WARNING
        return PAIR_SUCCESS

    def _flatten_rows(self, visible: list[TestResult]) -> list[FlatRow]:
        """Build scroll rows: project header, tests, optional condition lines."""
        out: list[FlatRow] = []
        for proj_key, group in self._contiguous_project_groups(visible):
            if proj_key is not None:
                out.append(("project", proj_key, group))
            for r in group:
                out.append(("test", r))
                if not self._show_conditions:
                    continue
                conds = self._conditions_for_result(r)
                for i in range(len(conds)):
                    out.append(("cond", r, i))
        return out

    def _clamp_scroll(self) -> None:
        """Keep scroll offset valid for the visible row count."""
        height, _ = self.get_dimensions()
        _, max_display = self._results_layout(height=height)
        visible = self._visible_results()
        n = len(self._flatten_rows(visible))
        max_offset = max(0, n - max_display)
        if self.scroll_offset > max_offset:
            self.scroll_offset = max_offset

    def _results_layout(self, *, height: int) -> tuple[int, int]:
        """Return (start_y, max_display) for the scrollable results list."""
        summary_y = 3 if self.summary.recorded_at else 2
        start_y = summary_y + 2
        max_display = max(0, height - start_y - 2)
        return start_y, max_display

    def render(self) -> None:
        """Render the test results."""
        self.clear()
        height, width = self.get_dimensions()

        # Header
        self.stdscr.attron(curses.color_pair(PAIR_HEADER))
        self.stdscr.addstr(0, 0, "Test Results")
        self.stdscr.attroff(curses.color_pair(PAIR_HEADER))

        if self.summary.recorded_at:
            run_line = f"Run: {self.summary.recorded_at.strftime('%Y-%m-%d %H:%M:%S')}"
            self.stdscr.addstr(1, 0, run_line[: width - 1])

        # Summary line
        summary_parts = []
        if self.summary.passed > 0:
            summary_parts.append(f"{self.summary.passed} passed")
        if self.summary.failed > 0:
            summary_parts.append(f"{self.summary.failed} failed")
        if self.summary.skipped > 0:
            summary_parts.append(f"{self.summary.skipped} skipped")
        if self.summary.errors > 0:
            summary_parts.append(f"{self.summary.errors} errors")

        summary_text = f"Total: {self.summary.total} | " + ", ".join(summary_parts)

        # Color the summary based on overall status
        summary_y = 3 if self.summary.recorded_at else 2
        if self.summary.all_passed:
            self.stdscr.attron(curses.color_pair(PAIR_SUCCESS))
            self.stdscr.addstr(summary_y, 0, summary_text[: width - 1])
            self.stdscr.attroff(curses.color_pair(PAIR_SUCCESS))
        else:
            self.stdscr.attron(curses.color_pair(PAIR_ERROR))
            self.stdscr.addstr(summary_y, 0, summary_text[: width - 1])
            self.stdscr.attroff(curses.color_pair(PAIR_ERROR))

        view_desc = self._view_description()
        filter_line = f"View: {view_desc}  (f: cycle filter, m: toggle condition rows)"
        self.stdscr.addstr(summary_y + 1, 0, filter_line[: width - 1])

        visible = self._visible_results()
        flat_rows = self._flatten_rows(visible)

        # Results list
        start_y, max_display = self._results_layout(height=height)

        if not visible:
            empty_msg = "No rows match this filter. Press f to change view."
            self.stdscr.addstr(start_y, 0, empty_msg[: width - 1])
        elif not flat_rows:
            pass
        else:
            for i in range(max_display):
                line_idx = self.scroll_offset + i
                if line_idx >= len(flat_rows):
                    break

                row = flat_rows[line_idx]
                y = start_y + i

                if row[0] == "project":
                    _, name, group = row
                    color = self._project_group_color(group=group)
                    line = self._format_project_header(name=name, width=width)
                    self.stdscr.attron(curses.color_pair(color))
                    self.stdscr.addstr(y, 0, line)
                    self.stdscr.attroff(curses.color_pair(color))
                elif row[0] == "test":
                    _, result = row
                    has_project = result.project_name is not None
                    line, color = self._format_test_line(
                        result=result,
                        width=width,
                        has_project=has_project,
                    )
                    self.stdscr.attron(curses.color_pair(color))
                    self.stdscr.addstr(y, 0, line)
                    self.stdscr.attroff(curses.color_pair(color))
                else:
                    _, result, sub_idx = row
                    has_project = result.project_name is not None
                    conds = self._conditions_for_result(result)
                    if sub_idx >= len(conds):
                        continue
                    cond = conds[sub_idx]
                    line, color = self._format_condition_line(
                        cond=cond,
                        width=width,
                        has_project=has_project,
                    )
                    self.stdscr.attron(curses.color_pair(color))
                    self.stdscr.addstr(y, 0, line)
                    self.stdscr.attroff(curses.color_pair(color))

        # Scroll indicator if needed
        if len(flat_rows) > max_display:
            end = min(self.scroll_offset + max_display, len(flat_rows))
            scroll_info = f"[{self.scroll_offset + 1}-{end}/{len(flat_rows)}]"
            self.stdscr.addstr(height - 2, width - len(scroll_info) - 1, scroll_info)

        det = "on" if self._show_conditions else "off"
        status = (
            f"f: filter ({self._result_filter.value}) | m: details {det} | "
            "arrows/jk: scroll | q: menu"
        )
        self.draw_status_bar(status[: width - 1])
        self.refresh()

    def handle_screen_event(self, *, key: int) -> None:
        """Handle keyboard input event."""
        self._handle_test_results_event(key=key)

    def _handle_test_results_event(self, *, key: int) -> None:
        """Process test results keyboard events."""
        height, _ = self.get_dimensions()
        _, max_display = self._results_layout(height=height)
        visible = self._visible_results()
        n = len(self._flatten_rows(visible))

        if key == ord("q"):
            self._go_back()

        elif key == ord("f"):
            self._cycle_filter()

        elif key == ord("m"):
            self._show_conditions = not self._show_conditions
            self._clamp_scroll()

        elif key == curses.KEY_UP or key == ord("k"):
            if self.scroll_offset > 0:
                self.scroll_offset -= 1

        elif key == curses.KEY_DOWN or key == ord("j"):
            max_offset = max(0, n - max_display)
            if self.scroll_offset < max_offset:
                self.scroll_offset += 1

        elif key == curses.KEY_PPAGE:  # Page Up
            self.scroll_offset = max(0, self.scroll_offset - max_display)

        elif key == curses.KEY_NPAGE:  # Page Down
            max_offset = max(0, n - max_display)
            self.scroll_offset = min(max_offset, self.scroll_offset + max_display)

    def _go_back(self) -> None:
        """Return to the main menu."""
        from inspectui.tui.screens.main_menu import MainMenuScreen  # noqa: PLC0415

        self.app.switch_screen(MainMenuScreen(self.app))

    def _format_params(self, params: dict[str, object]) -> str:
        """Format params for display."""
        parts: list[str] = []
        for key, value in params.items():
            if isinstance(value, list):
                value_str = ",".join(str(item) for item in value)
            else:
                value_str = str(value)
            parts.append(f"{key}={value_str}")
        return " ".join(parts)

    def _result_status_style(self, *, result: TestResult) -> tuple[str, int]:
        """Status marker and color pair for a test result."""
        if result.status == TestStatus.PASSED:
            return "✓", PAIR_SUCCESS
        if result.status == TestStatus.FAILED:
            return "✗", PAIR_ERROR
        if result.status == TestStatus.SKIPPED:
            return "-", PAIR_WARNING
        return "!", PAIR_ERROR

    def _format_project_header(self, *, name: str, width: int) -> str:
        """Project name only (color comes from ``_project_group_color``)."""
        line = name
        if len(line) > width - 1:
            line = line[: width - 4] + "..."
        return line

    def _format_test_line(
        self,
        *,
        result: TestResult,
        width: int,
        has_project: bool,
    ) -> tuple[str, int]:
        """Indented line: status, test name, message (no project prefix)."""
        status_char, color = self._result_status_style(result=result)
        indent = "    " if has_project else "  "
        params_text = ""
        if result.params:
            params_text = f" ({self._format_params(result.params)})"
        body = f"{status_char} {result.test_name}: {result.message}{params_text}"
        line = f"{indent}{body}"
        if len(line) > width - 1:
            line = line[: width - 4] + "..."
        return line, color

    def _format_condition_line(
        self,
        *,
        cond: dict[str, object],
        width: int,
        has_project: bool,
    ) -> tuple[str, int]:
        """Indented line for one condition under a test."""
        passed = bool(cond.get("passed"))
        status_char = "✓" if passed else "✗"
        color = PAIR_SUCCESS if passed else PAIR_ERROR
        label = str(cond.get("label", ""))
        detail = cond.get("detail")
        detail_s = f" — {detail}" if detail else ""
        indent = "        " if has_project else "    "
        line = f"{indent}{status_char} {label}{detail_s}"
        if len(line) > width - 1:
            line = line[: width - 4] + "..."
        return line, color
