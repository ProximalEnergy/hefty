"""Confirmation dialog component."""

import curses


def confirm_dialog(stdscr: curses.window, message: str) -> bool:
    """Display a yes/no confirmation dialog.

    Args:
        stdscr: The curses window.
        message: The message to display.

    Returns:
        True if user confirmed (y/Y), False otherwise.
    """
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    # Center the message
    y = height // 2 - 1
    x = max(0, (width - len(message)) // 2)
    stdscr.addstr(y, x, message[: width - 1])

    # Prompt
    prompt = "Press 'y' to confirm, any other key to cancel"
    x = max(0, (width - len(prompt)) // 2)
    stdscr.addstr(y + 2, x, prompt)

    stdscr.refresh()

    key = stdscr.getch()
    return key == ord("y") or key == ord("Y")


def show_message(stdscr: curses.window, message: str, wait: bool = True) -> None:
    """Display a message and optionally wait for key press.

    Args:
        stdscr: The curses window.
        message: The message to display.
        wait: Whether to wait for a key press.
    """
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    # Center the message
    y = height // 2
    x = max(0, (width - len(message)) // 2)
    stdscr.addstr(y, x, message[: width - 1])

    if wait:
        prompt = "Press any key to continue..."
        x = max(0, (width - len(prompt)) // 2)
        stdscr.addstr(y + 2, x, prompt)

    stdscr.refresh()

    if wait:
        stdscr.getch()
