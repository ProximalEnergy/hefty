#!/usr/bin/env python3
"""Switch kpi core dependency source in kpi/pyproject.toml."""

import argparse
import subprocess
import sys
from pathlib import Path


def parse_switch_core_source_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["editable", "codeartifact"],
        required=True,
        help="Dependency source mode for kpi core dependency.",
    )
    parser.add_argument(
        "--sync",
        dest="sync",
        action="store_true",
        default=True,
        help="Run uv sync in kpi directory when changes are made.",
    )
    parser.add_argument(
        "--no-sync",
        dest="sync",
        action="store_false",
        help="Skip uv sync after switching.",
    )
    return parser.parse_args()


def update_pyproject_toml(*, pyproject_path: Path, use_editable: bool) -> bool:
    """Update kpi pyproject.toml core source and dependency spec."""
    content = pyproject_path.read_text()
    lines = content.splitlines()

    sources_idx = None
    core_line_idx = None
    core_dependency_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if core_dependency_idx is None and stripped.startswith('"core'):
            core_dependency_idx = i
        if line.strip() == "[tool.uv.sources]":
            sources_idx = i
        elif sources_idx is not None and stripped.startswith("core ="):
            core_line_idx = i
            break

    if sources_idx is None:
        print("Error: [tool.uv.sources] section not found", file=sys.stderr)
        sys.exit(1)
    if core_line_idx is None:
        print("Error: core source line not found", file=sys.stderr)
        sys.exit(1)
    if core_dependency_idx is None:
        print("Error: core dependency line not found", file=sys.stderr)
        sys.exit(1)

    if use_editable:
        desired_source_line = 'core = { path = "../core", editable = true }'
        desired_dependency_line = '    "core",'
    else:
        desired_source_line = 'core = { index = "proximal-package-index" }'
        # Use prerelease-compatible spec so deploy resolves latest beta core.
        desired_dependency_line = '    "core>=0.0.0b0",'

    source_matches = lines[core_line_idx] == desired_source_line
    dependency_matches = lines[core_dependency_idx] == desired_dependency_line
    if source_matches and dependency_matches:
        return False

    lines[core_line_idx] = desired_source_line
    lines[core_dependency_idx] = desired_dependency_line
    pyproject_path.write_text("\n".join(lines) + "\n")
    return True


def switch_core_source_main() -> None:
    """Main entry point."""
    args = parse_switch_core_source_args()
    use_editable = args.mode == "editable"

    root_dir = Path(__file__).parent.parent
    pyproject_path = root_dir / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found", file=sys.stderr)
        sys.exit(1)

    changed = update_pyproject_toml(
        pyproject_path=pyproject_path, use_editable=use_editable
    )

    mode_label = "editable local core" if use_editable else "CodeArtifact"
    if changed:
        print(f"✓ Switched kpi to {mode_label}")
        print("  Updated: kpi/pyproject.toml")
        if args.sync:
            print("  Running 'uv sync'...")
            try:
                subprocess.run(["uv", "sync"], cwd=root_dir, check=True)
                print("✓ uv sync completed successfully")
            except subprocess.CalledProcessError as e:
                print(f"Error: uv sync failed with code {e.returncode}", file=sys.stderr)
                sys.exit(1)
    else:
        print(f"✓ kpi already configured for {mode_label}")


if __name__ == "__main__":
    switch_core_source_main()
