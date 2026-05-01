"""Capacity field check screen."""

import curses
from dataclasses import dataclass
from typing import TYPE_CHECKING

from inspectui.core.capacity_check import (
    CapacityCheckRow,
    MissingCapacityDevice,
    check_capacity_requirements,
)
from inspectui.core.models import ProjectInfo
from inspectui.tui.colors import PAIR_ERROR, PAIR_HEADER, PAIR_SUCCESS, PAIR_WARNING
from inspectui.tui.screens.base import BaseScreen

if TYPE_CHECKING:
    from inspectui.tui.app import InspectUIApp


@dataclass(frozen=True)
class ProjectCapacityRow:
    """Capacity check result scoped to one project."""

    project_name: str
    row: CapacityCheckRow


class CapacityCheckScreen(BaseScreen):
    """Screen for checking required device capacity fields."""

    def __init__(self, app: "InspectUIApp") -> None:
        super().__init__(app)
        self.rows: list[ProjectCapacityRow] = []
        self.errors: list[str] = []
        self.scroll_offset = 0
        self.show_all = False
        self._run_capacity_check()

    def _run_capacity_check(self) -> None:
        """Load active projects and check device capacity requirements."""
        active_projects, missing = self.app.get_active_projects()
        for name in missing:
            self.errors.append(f"{name}: project not found")
        if not active_projects:
            return

        total = len(active_projects)
        for idx, project in enumerate(active_projects, start=1):
            self._show_progress(project_name=project.name_short, idx=idx, total=total)
            if not self._load_project_data(project=project):
                self.errors.append(f"{project.name_short}: failed to load devices")
                continue
            if not self.app.cache_manager:
                self.errors.append(f"{project.name_short}: cache not available")
                continue
            for row in check_capacity_requirements(
                devices=self.app.cache_manager.devices,
            ):
                self.rows.append(
                    ProjectCapacityRow(project_name=project.name_short, row=row)
                )

    def _load_project_data(self, *, project: ProjectInfo) -> bool:
        """Load project device/tag data from cache or database."""
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

    def _visible_rows(self) -> list[ProjectCapacityRow]:
        """Return rows for the current filter."""
        if self.show_all:
            return list(self.rows)
        return [item for item in self.rows if not item.row.passed]

    def _clamp_scroll(self) -> None:
        """Keep scroll offset within visible row bounds."""
        height, _ = self.get_dimensions()
        max_display = self._max_display_rows(height=height)
        max_offset = max(0, len(self._visible_rows()) - max_display)
        self.scroll_offset = min(self.scroll_offset, max_offset)

    @staticmethod
    def _max_display_rows(*, height: int) -> int:
        """Rows available for result rendering."""
        return max(0, height - 6)

    def render(self) -> None:
        """Render the capacity check results."""
        self.clear()
        height, width = self.get_dimensions()

        self.stdscr.attron(curses.color_pair(PAIR_HEADER))
        self.stdscr.addstr(0, 0, "Capacity Field Check"[: width - 1])
        self.stdscr.attroff(curses.color_pair(PAIR_HEADER))

        failed = sum(1 for item in self.rows if not item.row.passed)
        passed = len(self.rows) - failed
        color = PAIR_SUCCESS if failed == 0 and not self.errors else PAIR_ERROR
        summary = (
            f"Rows: {len(self.rows)} | passed: {passed} | "
            f"failed: {failed} | errors: {len(self.errors)}"
        )
        self.stdscr.attron(curses.color_pair(color))
        self.stdscr.addstr(1, 0, summary[: width - 1])
        self.stdscr.attroff(curses.color_pair(color))

        view = "all rows" if self.show_all else "failing rows"
        self.stdscr.addstr(2, 0, f"View: {view} (t: toggle)"[: width - 1])

        if self.errors:
            self.stdscr.attron(curses.color_pair(PAIR_WARNING))
            errors_line = "Errors: " + "; ".join(self.errors)
            self.stdscr.addstr(3, 0, errors_line[: width - 1])
            self.stdscr.attroff(curses.color_pair(PAIR_WARNING))

        visible = self._visible_rows()
        max_display = self._max_display_rows(height=height)
        start_y = 5
        if not visible:
            msg = "No failing capacity fields." if self.rows else "No results to show."
            self.stdscr.addstr(start_y, 0, msg[: width - 1])
        else:
            for idx in range(max_display):
                row_idx = self.scroll_offset + idx
                if row_idx >= len(visible):
                    break
                item = visible[row_idx]
                line, row_color = self._format_row(item=item, width=width)
                self.stdscr.attron(curses.color_pair(row_color))
                self.stdscr.addstr(start_y + idx, 0, line)
                self.stdscr.attroff(curses.color_pair(row_color))

        if len(visible) > max_display:
            end = min(self.scroll_offset + max_display, len(visible))
            scroll_info = f"[{self.scroll_offset + 1}-{end}/{len(visible)}]"
            self.stdscr.addstr(height - 2, width - len(scroll_info) - 1, scroll_info)

        status = "t: toggle all/failing | arrows/jk: scroll | q: menu"
        self.draw_status_bar(status[: width - 1])
        self.refresh()

    def handle_screen_event(self, *, key: int) -> None:
        """Handle keyboard input event."""
        height, _ = self.get_dimensions()
        max_display = self._max_display_rows(height=height)
        max_offset = max(0, len(self._visible_rows()) - max_display)

        if key == ord("q"):
            self._go_back()
        elif key == ord("t"):
            self.show_all = not self.show_all
            self._clamp_scroll()
        elif key == curses.KEY_UP or key == ord("k"):
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif key == curses.KEY_DOWN or key == ord("j"):
            self.scroll_offset = min(max_offset, self.scroll_offset + 1)
        elif key == curses.KEY_PPAGE:
            self.scroll_offset = max(0, self.scroll_offset - max_display)
        elif key == curses.KEY_NPAGE:
            self.scroll_offset = min(max_offset, self.scroll_offset + max_display)

    def _format_row(self, *, item: ProjectCapacityRow, width: int) -> tuple[str, int]:
        """Format one result row."""
        row = item.row
        status = "OK" if row.passed else "MISS"
        color = PAIR_SUCCESS if row.passed else PAIR_ERROR
        req = row.requirement
        detail = self._missing_detail(missing=row.missing_devices)
        line = (
            f"{status} {item.project_name} | {req.device_type_label} | "
            f"{req.field_name} | {row.checked_count} checked"
        )
        if detail:
            line = f"{line} | missing: {detail}"
        if len(line) > width - 1:
            line = line[: width - 4] + "..."
        return line, color

    @staticmethod
    def _missing_detail(*, missing: tuple[MissingCapacityDevice, ...]) -> str:
        """Return a compact list of missing device labels."""
        if not missing:
            return ""
        labels = [f"{d.display_name} ({d.device_id})" for d in missing[:3]]
        if len(missing) > 3:
            labels.append(f"+{len(missing) - 3} more")
        return ", ".join(labels)

    def _show_progress(self, *, project_name: str, idx: int, total: int) -> None:
        """Show progress while loading project data."""
        self.clear()
        height, width = self.get_dimensions()
        msg = f"Checking capacity fields for {project_name} ({idx}/{total})..."
        self.stdscr.addstr(height // 2, max(0, (width - len(msg)) // 2), msg)
        self.refresh()

    def _go_back(self) -> None:
        """Return to the main menu."""
        from inspectui.tui.screens.main_menu import MainMenuScreen  # noqa: PLC0415

        self.app.switch_screen(MainMenuScreen(self.app))
