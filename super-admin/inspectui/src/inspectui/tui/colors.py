"""Color pair definitions for the TUI."""

import curses

# Color pair IDs
PAIR_HIGHLIGHT = 1  # Selected/highlighted item
PAIR_SELECTED = 2  # Multi-select checked item
PAIR_SUCCESS = 3  # Test passed / success message
PAIR_ERROR = 4  # Test failed / error message
PAIR_WARNING = 5  # Warning message
PAIR_HEADER = 6  # Header/title text
PAIR_STATUS = 7  # Status bar


def init_colors() -> None:
    """Initialize color pairs for the application."""
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(PAIR_HIGHLIGHT, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(PAIR_SELECTED, curses.COLOR_GREEN, -1)
    curses.init_pair(PAIR_SUCCESS, curses.COLOR_GREEN, -1)
    curses.init_pair(PAIR_ERROR, curses.COLOR_RED, -1)
    curses.init_pair(PAIR_WARNING, curses.COLOR_YELLOW, -1)
    curses.init_pair(PAIR_HEADER, curses.COLOR_CYAN, -1)
    curses.init_pair(PAIR_STATUS, curses.COLOR_BLACK, curses.COLOR_WHITE)
