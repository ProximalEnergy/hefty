#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether project.dependencies changed between revisions.",
    )
    parser.add_argument("--base", required=True, help="Base git revision")
    parser.add_argument("--head", required=True, help="Head git revision")
    parser.add_argument("--path", required=True, help="Path to pyproject.toml")
    return parser.parse_args()


def load_dependencies(*, revision: str, path: str) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        check=True,
        capture_output=True,
        text=True,
    )
    data = tomllib.loads(result.stdout)
    dependencies = data.get("project", {}).get("dependencies", [])
    if not isinstance(dependencies, list):
        raise TypeError(f"{path} project.dependencies must be a list")
    normalized = (dependency.strip() for dependency in dependencies)
    return tuple(sorted(normalized))


def main() -> int:
    args = parse_args()

    try:
        base_dependencies = load_dependencies(
            revision=args.base,
            path=args.path,
        )
        head_dependencies = load_dependencies(
            revision=args.head,
            path=args.path,
        )
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr, end="")
        return exc.returncode or 1
    except (tomllib.TOMLDecodeError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("true" if base_dependencies != head_dependencies else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
