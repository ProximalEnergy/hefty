#!/usr/bin/env python3
"""
Switch core dependency source based on git branch.

- staging/sandbox/main: Uses AWS CodeArtifact index
- all other branches: Uses editable local path (../core)
"""

import subprocess
import sys
from pathlib import Path


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

    Args:
        pyproject_path: TODO: describe.
        use_editable: TODO: describe.
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
        desired_line = 'core = { index = "proximal-package-index" }'

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
    use_editable = branch not in ["staging", "sandbox", "main"]

    # Update api/pyproject.toml
    api_pyproject = Path(__file__).parent.parent / "api" / "pyproject.toml"
    if not api_pyproject.exists():
        print(f"Error: {api_pyproject} not found", file=sys.stderr)
        sys.exit(1)

    changed = update_pyproject_toml(
        pyproject_path=api_pyproject, use_editable=use_editable
    )

    mode = (
        "editable local core" if use_editable else "CodeArtifact (staging/sandbox/main)"
    )

    if changed:
        print(f"✓ Switched to {mode}")
        print(f"  Updated: {api_pyproject.relative_to(Path.cwd())}")
        print("  Running 'uv sync'...")

        # Run uv sync in the api directory
        try:
            subprocess.run(
                ["uv", "sync"],
                cwd=api_pyproject.parent,
                check=True,
            )
            print("✓ uv sync completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error: uv sync failed with code {e.returncode}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"✓ Already configured for {mode}")


if __name__ == "__main__":
    main()
