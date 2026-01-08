#!/usr/bin/env python3
import curses
import os
import subprocess
import sys
import tempfile


def run_command(*, command):
    """Run a shell command and return stripped stdout or None on error."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_files_from_branch(*, branch):
    """Return files that differ from branch and exist on that branch."""
    # Get list of all files in the target branch
    cmd_ls = f"git ls-tree -r --name-only {branch}"
    output_ls = run_command(command=cmd_ls)
    if not output_ls:
        return []
    source_files = set(f for f in output_ls.split("\n") if f)

    # Get files that differ between current working directory and target branch
    cmd_diff = f"git diff --name-only {branch}"
    output_diff = run_command(command=cmd_diff)
    if not output_diff:
        return []
    diff_files = set(f for f in output_diff.split("\n") if f)

    # We only want files that exist in source AND differ
    valid_files = sorted(list(diff_files.intersection(source_files)))
    return valid_files


def get_branches():
    """Return local git branches as a list."""
    cmd = "git branch --format='%(refname:short)'"
    output = run_command(command=cmd)
    if output is None:
        return []
    return [b for b in output.split("\n") if b]


def get_current_branch():
    """Return current git branch or None when unavailable."""
    cmd = "git rev-parse --abbrev-ref HEAD"
    output = run_command(command=cmd)
    if output is None:
        return None
    return output.strip()


def select_items(*, stdscr, title, items, multi_select=False):
    """Render a list selection UI and return chosen items or None."""
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)

    current_row = 0
    selected_indices = set()
    offset = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Header
        if multi_select:
            instr = "(Space: toggle, Enter: confirm, q: quit)"
        else:
            instr = "(Enter: select, q: quit)"
        header = f"{title} {instr}"
        stdscr.addstr(0, 0, header[:width], curses.A_BOLD)

        max_display = height - 2

        for i in range(max_display):
            item_idx = i + offset
            if item_idx >= len(items):
                break

            item_name = items[item_idx]

            is_highlighted = item_idx == current_row
            is_selected = item_idx in selected_indices

            if multi_select:
                prefix = f"[{'x' if is_selected else ' '}] "
            else:
                prefix = "> " if is_highlighted else "  "

            display_text = f"{prefix}{item_name}"

            if len(display_text) > width:
                display_text = display_text[: width - 1]

            if is_highlighted:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(i + 1, 0, display_text)
                stdscr.attroff(curses.color_pair(1))
            elif is_selected:
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(i + 1, 0, display_text)
                stdscr.attroff(curses.color_pair(2))
            else:
                stdscr.addstr(i + 1, 0, display_text)

        stdscr.refresh()

        key = stdscr.getch()

        if key == ord("q"):
            return None
        elif key == curses.KEY_UP:
            if current_row > 0:
                current_row -= 1
                if current_row < offset:
                    offset -= 1
        elif key == curses.KEY_DOWN:
            if current_row < len(items) - 1:
                current_row += 1
                if current_row >= offset + max_display:
                    offset += 1
        elif key == ord(" "):
            if multi_select:
                if current_row in selected_indices:
                    selected_indices.remove(current_row)
                else:
                    selected_indices.add(current_row)
        elif key == ord("\n") or key == curses.KEY_ENTER:
            if multi_select:
                break
            else:
                return [items[current_row]]

    return [items[i] for i in selected_indices]


def confirm_action(*, stdscr, message):
    """Ask for a yes/no confirmation and return True if confirmed."""
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    stdscr.addstr(height // 2 - 1, (width - len(message)) // 2, message)
    option = "Press 'y' to confirm, any other key to cancel."
    stdscr.addstr(height // 2 + 1, (width - len(option)) // 2, option)
    stdscr.refresh()

    key = stdscr.getch()
    return key == ord("y") or key == ord("Y")


def merge_file(*, branch, file_path):
    """Merge one file from branch into current HEAD using git merge-file."""
    try:
        # 1. Check if file exists in current working directory
        if not os.path.exists(file_path):
            # If not in current, just checkout (copy)
            # But wait, checking out might overwrite untracked files? git handles this generally.
            print(f"File {file_path} not found locally. Copying from {branch}...")
            subprocess.run(
                f"git checkout {branch} -- {file_path}",
                shell=True,
                check=True,
            )
            return True

        # 2. Get merge base
        base_commit = run_command(command=f"git merge-base HEAD {branch}")
        if not base_commit:
            print(
                f"Could not find merge base. Falling back to checkout for {file_path}"
            )
            subprocess.run(
                f"git checkout {branch} -- {file_path}",
                shell=True,
                check=True,
            )
            return True

        # 3. Create temp files
        with (
            tempfile.NamedTemporaryFile(mode="w+", delete=False) as f_base,
            tempfile.NamedTemporaryFile(mode="w+", delete=False) as f_theirs,
        ):
            base_temp = f_base.name
            theirs_temp = f_theirs.name

        try:
            # 4. Populate temp files
            # Base version
            # Note: file might not exist in base
            cat_file_cmd = f"git cat-file -e {base_commit}:{file_path}"
            if run_command(command=cat_file_cmd) is not None:
                subprocess.run(
                    f"git show {base_commit}:{file_path} > {base_temp}",
                    shell=True,
                    check=True,
                )
            else:
                # If not in base, use empty file? Or treat as new?
                # git merge-file expects a base.
                pass

            # Their version
            subprocess.run(
                f"git show {branch}:{file_path} > {theirs_temp}",
                shell=True,
                check=True,
            )

            # 5. Run git merge-file
            # Usage: git merge-file <current-file> <base-file> <other-file>
            # This updates <current-file> in place with conflict markers if needed

            # We must handle the case where base didn't exist.
            # If base is empty/missing, it treats as 2-way merge?

            # Run merge-file
            # -L labels for conflict markers
            cmd = (
                "git merge-file -L current -L base "
                f"-L {branch} {file_path} {base_temp} {theirs_temp}"
            )
            result = subprocess.run(cmd, shell=True)

            # merge-file returns 0 on success, positive on conflict
            if result.returncode == 0:
                print(f"Merged {file_path}")
            else:
                print(f"Merged {file_path} with CONFLICTS")

        finally:
            # Cleanup
            if os.path.exists(base_temp):
                os.unlink(base_temp)
            if os.path.exists(theirs_temp):
                os.unlink(theirs_temp)

        return True

    except Exception as exc:
        print(f"Error merging {file_path}: {exc}")
        return False


def main(*, stdscr, branch):
    """Main curses flow for selecting branch and files to merge."""
    if not branch:
        branches = get_branches()
        if not branches:
            return "No branches found.", None, False

        current_branch = get_current_branch()
        if current_branch:
            title = f"Select source branch (current: {current_branch})"
        else:
            title = "Select source branch (current: unknown)"
        selection = select_items(
            stdscr=stdscr,
            title=title,
            items=branches,
            multi_select=False,
        )
        if not selection:
            return None, None, False
        branch = selection[0]

    # Fetch files
    stdscr.clear()
    stdscr.addstr(0, 0, f"Fetching files from {branch}...")
    stdscr.refresh()

    files = get_files_from_branch(branch=branch)
    if not files:
        return f"No different files found in branch {branch}", None, False

    title = f"Choose files from '{branch}'"
    selected_files = select_items(
        stdscr=stdscr,
        title=title,
        items=files,
        multi_select=True,
    )

    if not selected_files:
        return None, None, False

    # Confirmation inside TUI
    confirm_message = f"Attempt merge of {len(selected_files)} files from {branch}?"
    if confirm_action(stdscr=stdscr, message=confirm_message):
        return branch, selected_files, True
    else:
        return None, None, False


if __name__ == "__main__":
    branch_arg = None
    if len(sys.argv) > 1:
        branch_arg = sys.argv[1]
        if run_command(command=f"git rev-parse --verify {branch_arg}") is None:
            print(f"Error: Branch '{branch_arg}' does not exist.")
            sys.exit(1)

    try:
        result = curses.wrapper(
            lambda stdscr: main(stdscr=stdscr, branch=branch_arg),
        )
        # Restore terminal newline translation
        os.system("stty onlcr")

        if not result:
            sys.exit(0)

        final_branch, selected_files, confirmed = result

        if isinstance(final_branch, str) and selected_files is None:
            # Error message
            print(final_branch)
            sys.exit(0)

        if confirmed and selected_files:
            print(f"\nProcessing {len(selected_files)} files from {final_branch}...")
            for f in selected_files:
                merge_file(branch=final_branch, file_path=f)
            print("\nOperation complete.")
        else:
            if final_branch:
                print("\nCancelled or no files selected.")

    except Exception as e:
        print(f"Error: {e}")
