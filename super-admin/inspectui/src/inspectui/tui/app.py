"""InspectUIApp: wires config, DB, cache, and the initial curses screen."""

import curses
from typing import TYPE_CHECKING

from inspectui.core.cache import CacheManager
from inspectui.core.config import ConfigManager
from inspectui.core.database import DatabaseManager
from inspectui.core.fetcher import DataFetcher
from inspectui.core.repo_config import IGNORED_PROJECTS
from inspectui.tui.colors import init_colors
from inspectui.tui.screens.main_menu import MainMenuScreen

if TYPE_CHECKING:
    from inspectui.core.models import ProjectInfo
    from inspectui.tui.screens.base import BaseScreen


class InspectUIApp:
    """Main application class that manages screens and state."""

    def __init__(self) -> None:
        self.stdscr: curses.window | None = None
        self.db_manager: DatabaseManager | None = None
        self.data_fetcher: DataFetcher | None = None
        self.cache_manager: CacheManager | None = None
        self.config_manager: ConfigManager = ConfigManager()
        self.current_screen: BaseScreen | None = None
        self.running: bool = True

    def run(self, stdscr: curses.window) -> int:
        """Main application loop."""
        self.stdscr = stdscr
        curses.curs_set(0)
        init_colors()

        # Initialize database connection
        try:
            self.db_manager = DatabaseManager()
            self.data_fetcher = DataFetcher(self.db_manager)
            self.cache_manager = CacheManager()
        except Exception as e:
            self._show_error(f"Failed to connect to database: {e}")
            return 1

        # Load config
        self.config_manager.load()

        # Start with main menu
        self.current_screen = MainMenuScreen(self)

        while self.running:
            if self.current_screen:
                self.current_screen.render()
                key = stdscr.getch()
                self.current_screen.handle_input(key)

        # Save config on exit
        self.config_manager.save()

        return 0

    def switch_screen(self, screen: "BaseScreen") -> None:
        """Switch to a new screen."""
        self.current_screen = screen

    def quit(self) -> None:
        """Exit the application."""
        self.running = False

    def _show_error(self, message: str) -> None:
        """Display an error message and wait for key press."""
        if self.stdscr is None:
            return

        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        # Center the error message
        y = height // 2
        x = max(0, (width - len(message)) // 2)
        self.stdscr.addstr(y, x, message[: width - 1], curses.A_BOLD)

        prompt = "Press any key to exit..."
        x = max(0, (width - len(prompt)) // 2)
        self.stdscr.addstr(y + 2, x, prompt)

        self.stdscr.refresh()
        self.stdscr.getch()

    def get_active_project_names(self) -> list[str]:
        """Return active project names from config."""
        names = self.config_manager.get("active_projects", [])
        if isinstance(names, list):
            return [str(name) for name in names]
        return []

    def set_active_project_names(self, *, names: list[str]) -> None:
        """Persist active project names to config."""
        self.config_manager.set("active_projects", names)
        self.config_manager.save()

    def get_ignored_project_names(self) -> list[str]:
        """Return project name_shorts to hide from the project selector."""
        return list(IGNORED_PROJECTS)

    def get_active_projects(self) -> tuple[list["ProjectInfo"], list[str]]:
        """Return active projects and missing names."""
        names = self.get_active_project_names()
        if not names or not self.data_fetcher:
            return [], names

        projects = self.data_fetcher.fetch_all_projects()
        by_name = {project.name_short: project for project in projects}
        active = [by_name[name] for name in names if name in by_name]
        missing = [name for name in names if name not in by_name]
        return active, missing
