"""CLI entry: ``python -m inspectui`` or the ``inspectui`` script."""

import curses
import sys

try:
    import termios
except ImportError:
    termios = None

from inspectui.core.exception_messages import format_exception_message
from inspectui.tui.app import InspectUIApp


def _restore_tty_onlcr() -> None:
    """Re-enable ONLCR on the controlling tty (same effect as ``stty onlcr``).

    Skips silently when not a tty, ``termios`` is unavailable (e.g. Windows),
    or tcgetattr/tcsetattr fails.
    """
    if termios is None or not sys.stdin.isatty():
        return
    try:
        fd = sys.stdin.fileno()
        attrs = termios.tcgetattr(fd)
        attrs[1] |= termios.ONLCR
        termios.tcsetattr(fd, termios.TCSADRAIN, attrs)
    except OSError:
        pass


def main() -> int:
    """Main entry point for the InspectUI application."""
    try:
        app = InspectUIApp()
        result = curses.wrapper(app.run_application_loop)
        _restore_tty_onlcr()
        return result or 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        sys.stderr.write(f"Error: {format_exception_message(e)}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
