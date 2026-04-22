#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Final

NAME_RE: Final = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def requirement_name(*, requirement: str) -> str | None:
    match = NAME_RE.match(requirement)
    if match is None:
        return None
    return match.group(1).replace("_", "-").lower()


def resolve_requirement(
    *,
    pyproject_path: Path,
    dependency_group: str,
    package_name: str,
) -> str:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    dependency_groups = data.get("dependency-groups", {})
    dependencies = dependency_groups.get(dependency_group)

    if not isinstance(dependencies, list):
        raise SystemExit(
            f"dependency group '{dependency_group}' not found in {pyproject_path}"
        )

    normalized_package = package_name.replace("_", "-").lower()
    for dependency in dependencies:
        if not isinstance(dependency, str):
            continue
        if requirement_name(requirement=dependency) == normalized_package:
            return dependency

    raise SystemExit(
        f"dependency '{package_name}' not found in "
        f"{pyproject_path} group '{dependency_group}'"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run mypy in the current project env while pinning the mypy version "
            "from the monorepo root pyproject.toml."
        )
    )
    parser.add_argument(
        "--root-pyproject",
        default=Path(__file__).resolve().parent.parent / "pyproject.toml",
        type=Path,
        help="Path to the root pyproject.toml",
    )
    parser.add_argument(
        "--dependency-group",
        default="dev",
        help="dependency-groups key to read from the root pyproject.toml",
    )
    parser.add_argument(
        "--package-name",
        default="mypy",
        help="Package name to resolve from the dependency group",
    )
    return parser


def run_mypy(
    *,
    requirement: str,
    root_pyproject: Path,
    mypy_args: list[str],
) -> int:
    command = ["uv", "run", "--dev", "--with", requirement, "mypy"]
    has_config_file = "--config-file" in mypy_args or any(
        arg.startswith("--config-file=") for arg in mypy_args
    )
    if not has_config_file:
        command.extend(["--config-file", str(root_pyproject)])
    command.extend(mypy_args)

    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)

    completed = subprocess.run(command, env=env, check=False)
    return completed.returncode


def main() -> int:
    parser = build_parser()
    args, mypy_args = parser.parse_known_args()

    if not mypy_args:
        parser.error("pass arguments for mypy, for example: src/")

    requirement = resolve_requirement(
        pyproject_path=args.root_pyproject.resolve(),
        dependency_group=args.dependency_group,
        package_name=args.package_name,
    )
    return run_mypy(
        requirement=requirement,
        root_pyproject=args.root_pyproject.resolve(),
        mypy_args=mypy_args,
    )


if __name__ == "__main__":
    raise SystemExit(main())
