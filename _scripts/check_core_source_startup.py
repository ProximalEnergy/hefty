#!/usr/bin/env python3
"""
Startup check to warn if core dependency source might be misconfigured.

This script checks if the current git branch matches the expected core
source configuration and prints a warning if there's a mismatch.
"""

import subprocess
import sys
from pathlib import Path


def get_current_branch() -> str | None:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_current_core_source() -> str | None:
    """Get the current core source configuration from pyproject.toml."""
    try:
        pyproject_path = Path(__file__).parent.parent / "api" / "pyproject.toml"
        content = pyproject_path.read_text()

        # Find the core source line
        for line in content.splitlines():
            if line.strip().startswith("core ="):
                if "editable = true" in line:
                    return "editable"
                elif 'index = "proximal-package-index"' in line:
                    return "codeartifact"
        return None
    except (FileNotFoundError, OSError):
        return None


def main() -> None:
    """Check core source configuration and warn if mismatched."""
    branch = get_current_branch()
    if branch is None:
        # Not in a git repo or git not available, skip check
        return

    source = get_current_core_source()
    if source is None:
        # Could not determine source, skip check
        return

    # Check for mismatches
    should_be_editable = branch == "dev"
    is_editable = source == "editable"

    if should_be_editable and not is_editable:
        print(
            "⚠️  WARNING: You're on 'dev' branch but core is using CodeArtifact",
            file=sys.stderr,
        )
        print(
            "   Run 'mise run switch-core && uv sync' to use editable core",
            file=sys.stderr,
        )
        print(file=sys.stderr)
    elif not should_be_editable and is_editable:
        print(
            f"⚠️  WARNING: You're on '{branch}' branch but core is using "
            "editable local install",
            file=sys.stderr,
        )
        print(
            "   Run 'mise run switch-core && uv sync' to use CodeArtifact",
            file=sys.stderr,
        )
        print(file=sys.stderr)


if __name__ == "__main__":
    main()
