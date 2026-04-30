"""Reusable list selector component for single and multi-select."""

import curses
from collections.abc import Callable

from inspectui.tui.colors import PAIR_HIGHLIGHT, PAIR_SELECTED


class ListSelector[T]:
    """A reusable list selector component supporting single and multi-select."""

    def __init__(
        self,
        stdscr: curses.window,
        items: list[T],
        get_display: Callable[[T], str] | None = None,
        multi_select: bool = False,
        title: str = "",
        start_y: int = 1,
    ) -> None:
        """Initialize the list selector.

        Args:
            stdscr: The curses window to draw on.
            items: List of items to display.
            get_display: Function to convert item to display string. Uses str() if None.
            multi_select: Whether to allow multiple selections.
            title: Optional title to display above the list.
            start_y: Y coordinate to start rendering the list.
        """
        self.stdscr = stdscr
        self.items = items
        self.get_display = get_display or str
        self.multi_select = multi_select
        self.title = title
        self.start_y = start_y

        self.current_row = 0
        self.selected_indices: set[int] = set()
        self.offset = 0

    def render(self) -> None:
        """Render the list selector."""
        height, width = self.stdscr.getmaxyx()

        # Render title if provided
        if self.title:
            if self.multi_select:
                instr = "(Space: toggle, Enter: confirm, q: back)"
            else:
                instr = "(Enter: select, q: back)"
            header = f"{self.title} {instr}"
            self.stdscr.addstr(0, 0, header[: width - 1], curses.A_BOLD)

        max_display = height - self.start_y - 1

        for i in range(max_display):
            item_idx = i + self.offset
            if item_idx >= len(self.items):
                break

            item = self.items[item_idx]
            display_text = self.get_display(item)

            is_highlighted = item_idx == self.current_row
            is_selected = item_idx in self.selected_indices

            if self.multi_select:
                prefix = f"[{'x' if is_selected else ' '}] "
            else:
                prefix = "> " if is_highlighted else "  "

            full_text = f"{prefix}{display_text}"
            if len(full_text) > width - 1:
                full_text = full_text[: width - 4] + "..."

            y = i + self.start_y

            if is_highlighted:
                self.stdscr.attron(curses.color_pair(PAIR_HIGHLIGHT))
                self.stdscr.addstr(y, 0, full_text.ljust(width - 1))
                self.stdscr.attroff(curses.color_pair(PAIR_HIGHLIGHT))
            elif is_selected:
                self.stdscr.attron(curses.color_pair(PAIR_SELECTED))
                self.stdscr.addstr(y, 0, full_text)
                self.stdscr.attroff(curses.color_pair(PAIR_SELECTED))
            else:
                self.stdscr.addstr(y, 0, full_text)

    def handle_list_selector_event(
        self,
        *,
        key: int,
    ) -> tuple[bool, list[T] | None]:
        """Handle keyboard input event.

        Args:
            key: The key code from getch().

        Returns:
            Tuple of (should_continue, selected_items).
            should_continue is False if selection is complete or cancelled.
            selected_items is None if cancelled, list of selected items otherwise.
        """
        height, _ = self.stdscr.getmaxyx()
        max_display = height - self.start_y - 1

        if key == ord("q"):
            return False, None

        elif key == curses.KEY_UP or key == ord("k"):
            if self.current_row > 0:
                self.current_row -= 1
                if self.current_row < self.offset:
                    self.offset -= 1

        elif key == curses.KEY_DOWN or key == ord("j"):
            if self.current_row < len(self.items) - 1:
                self.current_row += 1
                if self.current_row >= self.offset + max_display:
                    self.offset += 1

        elif key == ord(" "):
            if self.multi_select:
                if self.current_row in self.selected_indices:
                    self.selected_indices.remove(self.current_row)
                else:
                    self.selected_indices.add(self.current_row)

        elif key == ord("\n") or key == curses.KEY_ENTER:
            if self.multi_select:
                return False, [self.items[i] for i in sorted(self.selected_indices)]
            else:
                if self.items:
                    return False, [self.items[self.current_row]]
                return False, []

        return True, None

    def get_current_item(self) -> T | None:
        """Get the currently highlighted item."""
        if 0 <= self.current_row < len(self.items):
            return self.items[self.current_row]
        return None
