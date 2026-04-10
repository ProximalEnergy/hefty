"""Project selection screen."""

import curses
from typing import TYPE_CHECKING

from inspectui.core.models import ProjectInfo
from inspectui.tui.colors import PAIR_HEADER, PAIR_HIGHLIGHT
from inspectui.tui.components.list_selector import ListSelector
from inspectui.tui.screens.base import BaseScreen

if TYPE_CHECKING:
    from inspectui.tui.app import InspectUIApp


class ProjectSelectScreen(BaseScreen):
    """Screen for selecting a project from the database."""

    def __init__(self, app: "InspectUIApp") -> None:
        super().__init__(app)
        self.all_projects: list[ProjectInfo] = []
        self.filter_query: str = ""
        self.filter_focus: bool = False
        self.selected_names: set[str] = set()
        self.selector: ListSelector[ProjectInfo] | None = None
        self.loading = True
        self.error: str | None = None
        self._load_projects()

    def _get_project_display(self, project: ProjectInfo) -> str:
        """Get display string for a project.

        Includes age of the per-project device/tag cache (optional fetch), if any.
        """
        base = f"{project.name_short} - {project.name_long}"
        cm = self.app.cache_manager
        if not cm:
            return base
        age = cm.get_cache_age(project.name_short)
        suffix = age or "not cached"
        return f"{base} · {suffix}"

    def _filtered_projects(self) -> list[ProjectInfo]:
        """Projects matching ``filter_query`` (substring, case-insensitive)."""
        q = self.filter_query.strip().lower()
        if not q:
            return list(self.all_projects)
        out: list[ProjectInfo] = []
        for p in self.all_projects:
            if q in p.name_short.lower() or q in p.name_long.lower():
                out.append(p)
        return out

    def _sync_selection_from_selector(self) -> None:
        """Merge list checkmarks into ``selected_names``; keeps hidden picks."""
        if not self.selector:
            return
        filtered = self._filtered_projects()
        visible = {p.name_short for p in filtered}
        self.selected_names = (self.selected_names - visible) | {
            filtered[i].name_short for i in self.selector.selected_indices
        }

    def _rebuild_selector(self) -> None:
        """Rebuild list UI from ``all_projects``, filter, and ``selected_names``."""
        filtered = self._filtered_projects()
        prev_row = self.selector.current_row if self.selector else 0

        self.selector = ListSelector(
            self.stdscr,
            filtered,
            get_display=self._get_project_display,
            multi_select=True,
            title="Select Active Projects",
            start_y=4,
        )
        self.selector.selected_indices = {
            i for i, p in enumerate(filtered) if p.name_short in self.selected_names
        }
        if not filtered:
            self.selector.current_row = 0
            self.selector.offset = 0
            return
        self.selector.current_row = min(prev_row, len(filtered) - 1)
        self.selector.offset = 0

    def _load_projects(self) -> None:
        """Load projects from the database."""
        try:
            if self.app.cache_manager:
                cached = self.app.cache_manager.load_projects_from_disk()
            else:
                cached = None

            if cached:
                raw = cached
            elif self.app.data_fetcher:
                raw = self.app.data_fetcher.fetch_all_projects()
                if self.app.cache_manager:
                    self.app.cache_manager.save_projects_to_disk(
                        projects=raw,
                    )
            else:
                raw = []

            ignored = set(self.app.get_ignored_project_names())
            self.all_projects = [p for p in raw if p.name_short not in ignored]

            self.selected_names = set(self.app.get_active_project_names())
            self.filter_query = ""
            self.filter_focus = False

            if self.all_projects:
                self._rebuild_selector()
            else:
                self.selector = None
            self.loading = False
        except Exception as e:
            self.loading = False
            self.error = str(e)

    def render(self) -> None:
        """Render the project selection screen."""
        self.clear()
        height, width = self.get_dimensions()

        if self.loading:
            msg = "Loading projects..."
            self.stdscr.addstr(height // 2, max(0, (width - len(msg)) // 2), msg)
            self.refresh()
            return

        if self.error:
            self.stdscr.attron(curses.color_pair(PAIR_HEADER))
            self.stdscr.addstr(1, 2, "Error loading projects")
            self.stdscr.attroff(curses.color_pair(PAIR_HEADER))
            self.stdscr.addstr(3, 2, self.error[: width - 4])
            self.stdscr.addstr(5, 2, "Press q to go back")
            self.refresh()
            return

        if not self.all_projects:
            self.stdscr.addstr(height // 2, 2, "No projects found in database")
            self.stdscr.addstr(height // 2 + 2, 2, "Press q to go back")
            self.refresh()
            return

        filtered = self._filtered_projects()
        filter_hint = (
            "Filter: type to narrow (Esc clear) | /: edit filter | Enter: leave filter"
        )
        self.stdscr.addstr(1, 0, filter_hint[: width - 1])

        filter_label = f"Filter: {self.filter_query}"
        if self.filter_focus:
            filter_label += "|"
        if self.filter_focus:
            self.stdscr.attron(curses.color_pair(PAIR_HIGHLIGHT))
            self.stdscr.addstr(2, 0, filter_label[: width - 1])
            self.stdscr.attroff(curses.color_pair(PAIR_HIGHLIGHT))
        else:
            self.stdscr.addstr(2, 0, filter_label[: width - 1])

        help_text = (
            "a: select all visible | n: deselect visible | r: refresh | "
            "Enter: save active"
        )
        self.stdscr.addstr(3, 0, help_text[: width - 1])

        if not filtered:
            msg = "No projects match filter"
            self.stdscr.addstr(5, 0, msg[: width - 1])
        elif self.selector:
            self.selector.render()

        n_all = len(self.all_projects)
        n_f = len(filtered)
        filt_note = f"{n_f} shown" if n_f != n_all else f"{n_all} projects"
        status = (
            f"{filt_note} | {len(self.selected_names)} active | "
            "Space: toggle, Enter: save, q: back"
        )
        self.draw_status_bar(status[: width - 1])
        self.refresh()

    def handle_input(self, key: int) -> None:
        """Handle keyboard input."""
        if self.loading or self.error:
            if key == ord("q"):
                self._go_back()
            return

        if not self.all_projects:
            if key == ord("q"):
                self._go_back()
            return

        if self.filter_focus:
            self._handle_filter_key(key=key)
            return

        if not self.selector:
            if key == ord("q"):
                self._go_back()
            return

        if key == ord("/"):
            self.filter_focus = True
            return

        if key == ord("a"):
            filtered = self._filtered_projects()
            self.selected_names |= {p.name_short for p in filtered}
            self._rebuild_selector()
            return

        if key == ord("n"):
            filtered = self._filtered_projects()
            self.selected_names -= {p.name_short for p in filtered}
            self._rebuild_selector()
            return

        if key == ord("r"):
            self._refresh_projects()
            return

        should_continue, selected = self.selector.handle_input(key)

        if should_continue:
            if key == ord(" "):
                self._sync_selection_from_selector()
            return

        if selected is not None:
            self._sync_selection_from_selector()
            self._save_active_projects()
        self._go_back()

    def _handle_filter_key(self, *, key: int) -> None:
        """Keys while the filter line is focused."""
        if key == ord("q"):
            self.filter_focus = False
            return

        if key == 27:  # Esc
            self.filter_query = ""
            self.filter_focus = False
            self._rebuild_selector()
            return

        if key in (curses.KEY_ENTER, ord("\n"), ord("\r")):
            self.filter_focus = False
            return

        if key in (curses.KEY_BACKSPACE, 127, 8):
            if self.filter_query:
                self.filter_query = self.filter_query[:-1]
                self._rebuild_selector()
            return

        if 32 <= key <= 126:
            if len(self.filter_query) < 120:
                self.filter_query += chr(key)
                self._rebuild_selector()
            return

    def _save_active_projects(self) -> None:
        """Persist the selected active projects."""
        names = sorted(self.selected_names)
        self.app.set_active_project_names(names=names)

    def _refresh_projects(self) -> None:
        """Refresh project list from the database."""
        if not self.app.data_fetcher:
            return

        self.clear()
        height, width = self.get_dimensions()
        msg = "Refreshing projects from database..."
        self.stdscr.addstr(height // 2, max(0, (width - len(msg)) // 2), msg)
        self.refresh()

        try:
            raw = self.app.data_fetcher.fetch_all_projects()
            if self.app.cache_manager:
                self.app.cache_manager.save_projects_to_disk(
                    projects=raw,
                )
            ignored = set(self.app.get_ignored_project_names())
            self.all_projects = [p for p in raw if p.name_short not in ignored]
            self.filter_query = ""
            self.filter_focus = False
            self._rebuild_selector()
        except Exception as e:
            self.error = str(e)

    def _go_back(self) -> None:
        """Return to the main menu."""
        from inspectui.tui.screens.main_menu import MainMenuScreen  # noqa: PLC0415

        self.app.switch_screen(MainMenuScreen(self.app))
