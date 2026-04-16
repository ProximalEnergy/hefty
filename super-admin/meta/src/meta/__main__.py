"""Terminal UI for recent git file churn."""

from __future__ import annotations

import curses
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

DEFAULT_LIMIT = 20
DEFAULT_SINCE = "3 months ago"
PACKAGE_REPO_ROOT = Path(__file__).resolve().parents[4]
LOCKFILE_NAMES = frozenset(
    {
        "bun.lock",
        "bun.lockb",
        "cargo.lock",
        "composer.lock",
        "gemfile.lock",
        "npm-shrinkwrap.json",
        "package-lock.json",
        "pipfile.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }
)
SortMode = Literal["lines", "touches"]


@dataclass(frozen=True)
class FileChange:
    """Aggregated git churn for a single file."""

    path: str
    added: int
    deleted: int
    touches: int

    @property
    def churn(self) -> int:
        """Return total line churn."""
        return self.added + self.deleted


def _run_git(*, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command and capture text output."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
    )


def _resolve_repo_root() -> Path:
    """Find the git repository root."""
    for candidate in (Path.cwd(), PACKAGE_REPO_ROOT):
        completed = _run_git(
            args=["rev-parse", "--show-toplevel"],
            cwd=candidate,
        )
        if completed.returncode == 0:
            return Path(completed.stdout.strip())

    raise RuntimeError("Could not find a git repository for meta.")


def _is_excluded_path(*, path: str) -> bool:
    """Return whether the path should be excluded from meta."""
    cleaned_path = path.replace("{", "").replace("}", "")
    filenames = [
        fragment.strip().rsplit("/", maxsplit=1)[-1].lower()
        for fragment in cleaned_path.split("=>")
    ]
    for filename in filenames:
        if filename == "schema.d.ts":
            return True
        if filename.endswith(".csv"):
            return True
        if filename in LOCKFILE_NAMES:
            return True
        if filename.endswith(".lock") or filename.endswith(".lockb"):
            return True
    return False


def _sort_changes(
    *,
    changes: list[FileChange],
    sort_mode: SortMode,
    limit: int,
) -> list[FileChange]:
    """Sort and truncate file churn results."""
    if sort_mode == "touches":
        key = lambda item: (-item.touches, -item.churn, item.path)
    else:
        key = lambda item: (-item.churn, -item.touches, item.path)

    return sorted(changes, key=key)[:limit]


def _load_changes(*, repo_root: Path, since: str) -> list[FileChange]:
    """Load file churn from git history."""
    completed = _run_git(
        args=[
            "log",
            f"--since={since}",
            "--numstat",
            "--format=commit %H",
            "--",
        ],
        cwd=repo_root,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "git log failed"
        raise RuntimeError(stderr)

    raw_stats: dict[str, dict[str, int]] = {}
    for line in completed.stdout.splitlines():
        if not line or line.startswith("commit "):
            continue

        parts = line.split("\t", maxsplit=2)
        if len(parts) != 3:
            continue

        added_text, deleted_text, path = parts
        if added_text == "-" or deleted_text == "-":
            continue
        if _is_excluded_path(path=path):
            continue

        stats = raw_stats.setdefault(
            path,
            {"added": 0, "deleted": 0, "touches": 0},
        )
        stats["added"] += int(added_text)
        stats["deleted"] += int(deleted_text)
        stats["touches"] += 1

    changes = [
        FileChange(
            path=path,
            added=stats["added"],
            deleted=stats["deleted"],
            touches=stats["touches"],
        )
        for path, stats in raw_stats.items()
    ]
    return changes


def _sort_mode_label(*, sort_mode: SortMode) -> str:
    """Return a user-facing sort label."""
    if sort_mode == "touches":
        return "touches"
    return "line churn"


def _truncate(*, text: str, width: int) -> str:
    """Fit text into the given width."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return f"{text[: width - 3]}..."


def _draw_line(
    *,
    stdscr: Any,
    row: int,
    text: str,
    width: int,
    attr: int = 0,
) -> None:
    """Draw a single clipped line."""
    height, _ = stdscr.getmaxyx()
    if row < 0 or row >= height:
        return
    if width <= 1:
        return
    try:
        stdscr.addnstr(
            row,
            0,
            _truncate(text=text, width=width - 1),
            width - 1,
            attr,
        )
    except curses.error:
        return


def _draw_screen(
    *,
    stdscr: Any,
    repo_root: Path,
    changes: list[FileChange],
    sort_mode: SortMode,
    last_refresh: str,
    error_message: str | None,
) -> None:
    """Render the full screen."""
    stdscr.erase()
    height, width = stdscr.getmaxyx()

    _draw_line(
        stdscr=stdscr,
        row=0,
        text="Meta",
        width=width,
        attr=curses.A_BOLD,
    )
    _draw_line(
        stdscr=stdscr,
        row=1,
        text=(
            f"Top {DEFAULT_LIMIT} files by {_sort_mode_label(sort_mode=sort_mode)} "
            f"in the last {DEFAULT_SINCE}"
        ),
        width=width,
    )
    _draw_line(
        stdscr=stdscr,
        row=2,
        text=f"Repo: {repo_root}",
        width=width,
    )
    _draw_line(
        stdscr=stdscr,
        row=3,
        text=f"Last refresh: {last_refresh}",
        width=width,
    )
    _draw_line(
        stdscr=stdscr,
        row=4,
        text="Excluded: lockfiles, schema.d.ts, *.csv",
        width=width,
    )

    if error_message is not None:
        _draw_line(
            stdscr=stdscr,
            row=6,
            text=f"Error: {error_message}",
            width=width,
            attr=curses.A_BOLD,
        )
        _draw_line(
            stdscr=stdscr,
            row=height - 1,
            text="r refresh   s sort   l lines   t touches   q quit",
            width=width,
        )
        stdscr.refresh()
        return

    _draw_line(
        stdscr=stdscr,
        row=6,
        text=" #   churn       +       - touches  path",
        width=width,
        attr=curses.A_BOLD,
    )

    max_rows = max(height - 8, 0)
    for index, change in enumerate(changes[:max_rows], start=1):
        line = (
            f"{index:>2} {change.churn:>7} {change.added:>7} "
            f"{change.deleted:>7} {change.touches:>7}  {change.path}"
        )
        _draw_line(
            stdscr=stdscr,
            row=6 + index,
            text=line,
            width=width,
        )

    _draw_line(
        stdscr=stdscr,
        row=height - 1,
        text="r refresh   s sort   l lines   t touches   q quit",
        width=width,
    )
    stdscr.refresh()


def _run_app(*, stdscr: Any, repo_root: Path) -> int:
    """Run the curses event loop."""
    try:
        curses.curs_set(0)
    except curses.error:
        pass

    last_refresh = ""
    all_changes: list[FileChange] = []
    changes: list[FileChange] = []
    error_message: str | None = None
    sort_mode: SortMode = "lines"

    def sort_visible_changes() -> None:
        nonlocal changes
        changes = _sort_changes(
            changes=all_changes,
            sort_mode=sort_mode,
            limit=DEFAULT_LIMIT,
        )

    def refresh() -> None:
        nonlocal all_changes, error_message, last_refresh
        try:
            all_changes = _load_changes(
                repo_root=repo_root,
                since=DEFAULT_SINCE,
            )
            sort_visible_changes()
            error_message = None
        except RuntimeError as exc:
            error_message = str(exc)
        last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    refresh()

    while True:
        _draw_screen(
            stdscr=stdscr,
            repo_root=repo_root,
            changes=changes,
            sort_mode=sort_mode,
            last_refresh=last_refresh,
            error_message=error_message,
        )
        key = stdscr.getch()
        if key in {ord("q"), ord("Q")}:
            return 0
        if key in {ord("r"), ord("R")}:
            refresh()
        if key in {ord("s"), ord("S")}:
            sort_mode = "touches" if sort_mode == "lines" else "lines"
            sort_visible_changes()
        if key in {ord("l"), ord("L")}:
            sort_mode = "lines"
            sort_visible_changes()
        if key in {ord("t"), ord("T")}:
            sort_mode = "touches"
            sort_visible_changes()


def main() -> int:
    """Run the meta TUI."""
    try:
        repo_root = _resolve_repo_root()
        return curses.wrapper(
            lambda stdscr: _run_app(
                stdscr=stdscr,
                repo_root=repo_root,
            )
        )
    except KeyboardInterrupt:
        return 0
    except RuntimeError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
