"""Text input component for parameter entry."""

import curses

from inspectui.tui.colors import PAIR_HEADER


def get_text_input(
    stdscr: curses.window,
    prompt: str,
    default: str = "",
    description: str = "",
) -> str | None:
    """Display a text input prompt and return user input.

    Args:
        stdscr: The curses window.
        prompt: The prompt text (e.g., "Device type IDs:").
        default: Default value to pre-fill.
        description: Optional description shown below prompt.

    Returns:
        The entered text, or None if cancelled (Escape pressed).
    """
    curses.curs_set(1)  # Show cursor
    curses.echo()

    height, width = stdscr.getmaxyx()
    stdscr.clear()

    # Draw prompt
    y = height // 3
    stdscr.attron(curses.color_pair(PAIR_HEADER))
    stdscr.addstr(y, 2, prompt[: width - 4])
    stdscr.attroff(curses.color_pair(PAIR_HEADER))

    # Draw description if provided
    if description:
        stdscr.addstr(y + 1, 2, description[: width - 4])

    # Draw input field
    input_y = y + 3
    stdscr.addstr(input_y, 2, "> ")

    # Show default value hint
    if default:
        default_str = str(default)
        hint = f"(default: {default_str})"
        stdscr.addstr(input_y + 2, 2, hint[: width - 4])

    stdscr.addstr(height - 2, 2, "Enter: confirm | Esc: cancel")
    stdscr.refresh()

    # Get input
    curses.noecho()
    curses.curs_set(0)

    # Manual input handling for better control
    input_text = ""

    while True:
        # Redraw input area
        stdscr.move(input_y, 4)
        stdscr.clrtoeol()
        stdscr.addstr(input_y, 4, input_text[: width - 6])
        stdscr.move(input_y, 4 + len(input_text))
        curses.curs_set(1)
        stdscr.refresh()

        key = stdscr.getch()

        if key == 27:  # Escape
            curses.curs_set(0)
            return None

        elif key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            curses.curs_set(0)
            # Return default if empty
            if not input_text and default:
                return str(default)
            return input_text

        elif key in (curses.KEY_BACKSPACE, 127, 8):
            if input_text:
                input_text = input_text[:-1]

        elif key == curses.KEY_DC:  # Delete
            pass  # Could implement delete at cursor

        elif 32 <= key <= 126:  # Printable characters
            if len(input_text) < width - 8:
                input_text += chr(key)


def get_multiple_params(
    stdscr: curses.window,
    params: list[tuple[str, str, str, str]],  # (name, prompt, description, default)
) -> dict[str, str] | None:
    """Get multiple parameter values from the user.

    Args:
        stdscr: The curses window.
        params: List of (name, prompt, description, default) tuples.

    Returns:
        Dictionary of parameter name -> value, or None if cancelled.
    """
    result = {}

    for name, prompt, description, default in params:
        value = get_text_input(stdscr, prompt, default, description)
        if value is None:
            return None
        result[name] = value

    return result
