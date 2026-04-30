#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bump core patch version if it is behind a base revision.",
    )
    parser.add_argument(
        "--base-revision",
        required=True,
        help="Git revision to compare against, e.g. origin/dev",
    )
    parser.add_argument(
        "--pyproject-path",
        default="core/pyproject.toml",
        help="Path to the core pyproject.toml file",
    )
    return parser.parse_args()


def parse_release(*, version: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        raise ValueError(
            f"Unsupported version '{version}'. Expected major.minor.patch.",
        )
    return tuple(int(part) for part in match.groups())


def load_worktree_version(*, pyproject_path: Path) -> str:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return data["project"]["version"]


def load_revision_version(*, revision: str, pyproject_path: Path) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:{pyproject_path.as_posix()}"],
        check=True,
        capture_output=True,
        text=True,
    )
    data = tomllib.loads(result.stdout)
    return data["project"]["version"]


def write_bumped_version(*, pyproject_path: Path, new_version: str) -> None:
    updated_text = re.sub(
        r'(?m)^version\s*=\s*"[^"]+"\s*$',
        f'version = "{new_version}"',
        pyproject_path.read_text(encoding="utf-8"),
        count=1,
    )
    pyproject_path.write_text(updated_text, encoding="utf-8")


def auto_bump_core_version() -> int:
    args = parse_args()
    pyproject_path = Path(args.pyproject_path)

    try:
        current_version = load_worktree_version(pyproject_path=pyproject_path)
        base_version = load_revision_version(
            revision=args.base_revision,
            pyproject_path=pyproject_path,
        )
        current_release = parse_release(version=current_version)
        base_release = parse_release(version=base_version)
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr, end="")
        return exc.returncode or 1
    except (
        FileNotFoundError,
        KeyError,
        tomllib.TOMLDecodeError,
        ValueError,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"PR version: {current_version}", file=sys.stderr)
    print(f"dev version: {base_version}", file=sys.stderr)

    bumped = "false"
    new_version = current_version

    if current_release < base_release:
        major, minor, patch = base_release
        new_version = f"{major}.{minor}.{patch + 1}"
        write_bumped_version(
            pyproject_path=pyproject_path,
            new_version=new_version,
        )
        bumped = "true"
        print(
            "PR version is lower than dev. "
            f"Bumping patch version to {new_version}.",
            file=sys.stderr,
        )
    else:
        print(
            "PR version is not lower than dev. No change needed.",
            file=sys.stderr,
        )

    print(f"bumped={bumped}")
    print(f"new_version={new_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(auto_bump_core_version())
