"""Base screen class for TUI screens."""

import curses
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from inspectui.tui.colors import PAIR_STATUS

if TYPE_CHECKING:
    from inspectui.tui.app import InspectUIApp


class BaseScreen(ABC):
    """Abstract base class for all TUI screens."""

    def __init__(self, app: "InspectUIApp") -> None:
        """Initialize the screen.

        Args:
            app: The main application instance.
        """
        self.app = app
        self.stdscr = app.stdscr

    @abstractmethod
    def render(self) -> None:
        """Render the screen content."""

    @abstractmethod
    def handle_input(self, key: int) -> None:
        """Handle keyboard input.

        Args:
            key: The key code from getch().
        """

    def clear(self) -> None:
        """Clear the screen."""
        if self.stdscr:
            self.stdscr.clear()

    def refresh(self) -> None:
        """Refresh the screen."""
        if self.stdscr:
            self.stdscr.refresh()

    def get_dimensions(self) -> tuple[int, int]:
        """Get the screen dimensions.

        Returns:
            Tuple of (height, width).
        """
        if self.stdscr:
            return self.stdscr.getmaxyx()
        return 0, 0

    def draw_header(self, text: str, y: int = 0) -> None:
        """Draw a header line.

        Args:
            text: The header text.
            y: The y coordinate.
        """
        if self.stdscr:
            _, width = self.get_dimensions()
            self.stdscr.addstr(y, 0, text[: width - 1], curses.A_BOLD)

    def draw_status_bar(self, text: str) -> None:
        """Draw a status bar at the bottom of the screen.

        Args:
            text: The status bar text.
        """
        if self.stdscr:
            height, width = self.get_dimensions()
            self.stdscr.attron(curses.color_pair(PAIR_STATUS))
            self.stdscr.addstr(height - 1, 0, text.ljust(width - 1)[: width - 1])
            self.stdscr.attroff(curses.color_pair(PAIR_STATUS))
