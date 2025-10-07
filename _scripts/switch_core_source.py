#!/usr/bin/env python3
"""
Switch core dependency source based on git branch.

- dev: Uses editable local path (../core)
- staging/main: Uses AWS CodeArtifact index
"""

import subprocess
import sys
from pathlib import Path

import tomllib


def get_current_branch() -> str:
    """Get the current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def update_pyproject_toml(*, pyproject_path: Path, use_editable: bool) -> bool:
    """Update pyproject.toml with the appropriate core source.

    Returns True if changes were made, False if already correct.
    """
    content = pyproject_path.read_text()
    lines = content.splitlines()

    # Find the [tool.uv.sources] section
    sources_idx = None
    core_line_idx = None

    for i, line in enumerate(lines):
        if line.strip() == "[tool.uv.sources]":
            sources_idx = i
        elif sources_idx is not None and line.strip().startswith("core ="):
            core_line_idx = i
            break

    if sources_idx is None:
        print("Error: [tool.uv.sources] section not found", file=sys.stderr)
        sys.exit(1)

    if core_line_idx is None:
        print("Error: core source line not found", file=sys.stderr)
        sys.exit(1)

    # Determine the desired line
    if use_editable:
        desired_line = 'core = { path = "../core", editable = true }'
    else:
        desired_line = 'core = { index = "proximal" }'

    # Check if already correct
    if lines[core_line_idx] == desired_line:
        return False

    # Update the core line
    lines[core_line_idx] = desired_line

    # Write back to file
    pyproject_path.write_text("\n".join(lines) + "\n")
    return True


def main() -> None:
    """Main entry point."""
    # Get current branch
    try:
        branch = get_current_branch()
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)

    # Determine which source to use
    use_editable = branch == "dev"

    # Update api/pyproject.toml
    api_pyproject = Path(__file__).parent.parent / "api" / "pyproject.toml"
    if not api_pyproject.exists():
        print(f"Error: {api_pyproject} not found", file=sys.stderr)
        sys.exit(1)

    changed = update_pyproject_toml(
        pyproject_path=api_pyproject, use_editable=use_editable
    )

    if changed:
        mode = (
            "editable local core (dev)"
            if use_editable
            else "CodeArtifact (staging/main)"
        )
        print(f"✓ Switched to {mode}")
        print(f"  Updated: {api_pyproject.relative_to(Path.cwd())}")
        print("  Run 'uv sync' to apply the changes.")
    else:
        # Already correct, silent success
        pass


if __name__ == "__main__":
    main()
