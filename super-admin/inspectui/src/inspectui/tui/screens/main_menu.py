"""Main menu screen."""

import curses
from pathlib import Path
from typing import TYPE_CHECKING

from inspectui.core.csv_loader import (
    default_csv_directory,
    load_devices_csv,
    project_devices_csv_path,
)
from inspectui.tui.colors import PAIR_HEADER, PAIR_HIGHLIGHT
from inspectui.tui.components.text_input import get_text_input
from inspectui.tui.screens.base import BaseScreen
from inspectui.tui.screens.project_select import ProjectSelectScreen
from inspectui.tui.screens.test_results import TestResultsScreen
from inspectui.tui.screens.test_select import TestSelectScreen

if TYPE_CHECKING:
    from inspectui.tui.app import InspectUIApp


class MainMenuScreen(BaseScreen):
    """Main menu screen with navigation options."""

    MENU_ITEMS = [
        ("Manage Active Projects", "project_select"),
        ("Download Active Projects (Database)", "download_active_db"),
        ("Load Active Projects (CSV)", "load_active_csv"),
        ("Run Tests (Active Projects)", "test_select"),
        ("Last Test Run Results", "last_test_results"),
        ("Quit", "quit"),
    ]

    def __init__(self, app: "InspectUIApp") -> None:
        super().__init__(app)
        self.current_row = 0

    def render(self) -> None:
        """Render the main menu."""
        self.clear()
        height, width = self.get_dimensions()

        # Title
        title = "InspectUI - Database Inspection Tool"
        self.stdscr.attron(curses.color_pair(PAIR_HEADER))
        self.stdscr.addstr(1, max(0, (width - len(title)) // 2), title)
        self.stdscr.attroff(curses.color_pair(PAIR_HEADER))

        active = self.app.get_active_project_names()
        if active:
            count_line = f"Active projects: {len(active)}"
            self.stdscr.addstr(3, 2, count_line[: width - 4])
            names_line = ", ".join(active[:4])
            if len(active) > 4:
                names_line += ", ..."
            list_line = f"Active list: {names_line}"
            self.stdscr.addstr(4, 2, list_line[: width - 4])
            start_y = 6
        else:
            self.stdscr.addstr(3, 2, "No active projects selected")
            start_y = 5

        # Menu items
        for i, (label, _) in enumerate(self.MENU_ITEMS):
            y = start_y + i
            if i == self.current_row:
                self.stdscr.attron(curses.color_pair(PAIR_HIGHLIGHT))
                self.stdscr.addstr(y, 2, f"> {label}".ljust(width - 4))
                self.stdscr.attroff(curses.color_pair(PAIR_HIGHLIGHT))
            else:
                self.stdscr.addstr(y, 2, f"  {label}")

        # Status bar
        self.draw_status_bar("Use arrows/jk to navigate, Enter to select, q to quit")

        self.refresh()

    def handle_input(self, key: int) -> None:
        """Handle keyboard input."""
        if key == ord("q"):
            self.app.quit()

        elif key == curses.KEY_UP or key == ord("k"):
            self.current_row = max(0, self.current_row - 1)

        elif key == curses.KEY_DOWN or key == ord("j"):
            self.current_row = min(len(self.MENU_ITEMS) - 1, self.current_row + 1)

        elif key == ord("\n") or key == curses.KEY_ENTER:
            _, action = self.MENU_ITEMS[self.current_row]
            self._handle_action(action=action)

    def _handle_action(self, *, action: str) -> None:
        """Handle menu action selection."""
        if action == "quit":
            self.app.quit()
        elif action == "project_select":
            self.app.switch_screen(ProjectSelectScreen(self.app))
        elif action == "download_active_db":
            self._download_active_projects_from_database()
        elif action == "load_active_csv":
            self._load_active_projects_from_csv()
        elif action == "test_select":
            active = self.app.get_active_project_names()
            if not active:
                self._show_message(message="No active projects selected.")
                return
            self.app.switch_screen(TestSelectScreen(self.app))
        elif action == "last_test_results":
            if not self.app.cache_manager:
                self._show_message(message="Cache is not available.")
                return
            summary = self.app.cache_manager.load_last_test_run()
            if summary is None:
                self._show_message(
                    message="No saved test run yet. Run tests from the menu first.",
                )
                return
            self.app.switch_screen(TestResultsScreen(self.app, summary))

    def _download_active_projects_from_database(self) -> None:
        """Fetch device/tag data from the database for all active projects."""
        if not self.app.data_fetcher or not self.app.cache_manager:
            self._show_message(message="Data fetcher is not available.")
            return

        active_projects, missing = self.app.get_active_projects()
        if not active_projects:
            self._show_message(message="No active projects selected.")
            return

        errors: list[str] = []
        total = len(active_projects)
        for idx, project in enumerate(active_projects, start=1):
            self.clear()
            height, width = self.get_dimensions()
            msg = f"Fetching {project.name_short} ({idx}/{total})..."
            self.stdscr.addstr(height // 2, max(0, (width - len(msg)) // 2), msg)
            self.refresh()
            try:
                devices = self.app.data_fetcher.fetch_devices(project.name_short)
                tags = self.app.data_fetcher.fetch_tags(project.name_short)
                self.app.cache_manager.set_project(project, devices, tags)
            except Exception as e:
                errors.append(f"{project.name_short}: {e}")

        if missing:
            missing_list = ", ".join(missing)
            errors.append(f"Missing projects: {missing_list}")

        if errors:
            message = "Download completed with errors."
            self._show_message(message=message, details=errors)
            return

        self._show_message(message="Downloaded active projects from database.")

    def _resolve_csv_data_root(self) -> Path | None:
        """Return directory containing ``{project} - devices.csv`` CSV files.

        Defaults to ``~/Downloads`` on macOS when unset. Prompts only if that
        path is missing or the user must choose another folder.
        """
        cm = self.app.config_manager
        raw = cm.get("csv_data_root", "") if cm else ""
        if isinstance(raw, str) and raw.strip():
            p = Path(raw).expanduser()
            if p.is_dir():
                return p.resolve()

        downloads = default_csv_directory()
        if downloads.is_dir():
            return downloads

        default_str = str(Path.home() / "Downloads")
        entered = get_text_input(
            self.stdscr,
            "CSV directory:",
            default=default_str,
            description=(
                "Folder containing '<project> - devices.csv' "
                "(tags load from DB). Default ~/Downloads. "
                "Enter to confirm, Esc to cancel."
            ),
        )
        if entered is None:
            return None
        p = Path(entered.strip()).expanduser()
        if not p.is_dir():
            self._show_message(message=f"Not a directory: {p}")
            return None
        resolved = p.resolve()
        if cm:
            cm.set("csv_data_root", str(resolved))
            cm.save()
        return resolved

    def _load_active_projects_from_csv(self) -> None:
        """Load devices from CSV; tags from the database (when connected)."""
        if not self.app.cache_manager:
            self._show_message(message="Cache is not available.")
            return

        active_projects, missing = self.app.get_active_projects()
        if not active_projects:
            self._show_message(message="No active projects selected.")
            return

        root = self._resolve_csv_data_root()
        if root is None:
            return

        errors: list[str] = []
        total = len(active_projects)
        for idx, project in enumerate(active_projects, start=1):
            self.clear()
            height, width = self.get_dimensions()
            msg = f"Loading {project.name_short} devices from CSV ({idx}/{total})..."
            self.stdscr.addstr(height // 2, max(0, (width - len(msg)) // 2), msg)
            self.refresh()
            devices_path = project_devices_csv_path(
                root=root,
                name_short=project.name_short,
            )
            try:
                devices = load_devices_csv(path=devices_path)
                if self.app.data_fetcher:
                    tags = self.app.data_fetcher.fetch_tags(project.name_short)
                else:
                    tags = []
                self.app.cache_manager.set_project(project, devices, tags)
            except Exception as e:
                errors.append(f"{project.name_short}: {e}")

        if missing:
            missing_list = ", ".join(missing)
            errors.append(f"Missing projects: {missing_list}")

        if errors:
            self._show_message(
                message="CSV load completed with errors.",
                details=errors,
            )
            return

        self._show_message(
            message="Loaded devices from CSV; tags loaded from database.",
        )

    def _show_message(
        self,
        *,
        message: str,
        details: list[str] | None = None,
    ) -> None:
        """Show a message and wait for a key press."""
        self.clear()
        height, width = self.get_dimensions()
        self.stdscr.attron(curses.color_pair(PAIR_HEADER))
        self.stdscr.addstr(height // 2 - 1, 2, message[: width - 4])
        self.stdscr.attroff(curses.color_pair(PAIR_HEADER))
        if details:
            y = height // 2 + 1
            for line in details[: max(0, height - y - 2)]:
                self.stdscr.addstr(y, 2, line[: width - 4])
                y += 1
        self.stdscr.addstr(height - 2, 2, "Press any key to continue...")
        self.refresh()
        if self.stdscr:
            self.stdscr.getch()
