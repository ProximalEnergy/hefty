#!/usr/bin/env python3
"""Ensure functions with parameters include an Args block in docstrings."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path


def parse_args(*, argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        argv: Command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Ensure Python docstrings include Args sections using Semgrep"
    )
    parser.add_argument(
        "repository",
        help="Repository to check (api or core)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific files or directories to check",
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        help=(
            "Directory to scan when no explicit paths are provided. "
            "Defaults to the repository directory."
        ),
    )
    return parser.parse_args(argv)


def main(*, argv: Sequence[str] | None = None) -> int:
    """Run semgrep check.

    Args:
        argv: Command line arguments.
    """
    args = parse_args(argv=argv)

    # Determine the default directory based on repository argument
    if args.directory:
        target_path = args.directory
    else:
        # Find the mono repository root (assumes script is in mono/_scripts)
        script_path = Path(__file__).resolve()
        mono_root = script_path.parent.parent
        target_path = mono_root / args.repository

    paths_to_check = args.paths if args.paths else [str(target_path)]

    # Locate the rule file
    rule_file = Path(__file__).parent / "rules" / "docstring-args.yaml"

    cmd = [
        "uv",
        "run",
        "semgrep",
        "--config",
        str(rule_file),
        "--error",  # Return exit code 1 on error
        "--quiet",  # Less verbose
        "--exclude",
        "*_alembic_migrations*",
        "--exclude",
        "alembic",
        "--exclude",
        "tests",
        "--exclude",
        "_tests",
        "--exclude",
        "route_tree.py",
    ] + paths_to_check

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
