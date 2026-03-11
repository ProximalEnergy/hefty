#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "field",
        choices=("core-version", "package-index-url"),
    )
    return parser


def load_project() -> Mapping[str, Any]:
    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as file_handle:
        return tomllib.load(file_handle)


def read_core_version(*, project: Mapping[str, Any]) -> str:
    dependencies = project["project"]["dependencies"]
    core_specs = [dep for dep in dependencies if dep.startswith("core")]

    if len(core_specs) != 1:
        message = (
            "Expected exactly one core dependency entry, "
            f"found {len(core_specs)}."
        )
        raise SystemExit(message)

    match = re.fullmatch(
        r"core==([A-Za-z0-9][A-Za-z0-9._+-]*)",
        core_specs[0],
    )
    if match is None:
        raise SystemExit(
            "core dependency must be pinned as core==x.y.z in pyproject.toml."
        )

    return match.group(1)


def read_package_index_url(*, project: Mapping[str, Any]) -> str:
    indexes = project.get("tool", {}).get("uv", {}).get("index", [])
    matching_urls = [
        index["url"]
        for index in indexes
        if index.get("name") == "proximal-package-index"
    ]

    if len(matching_urls) != 1:
        raise SystemExit(
            "Expected exactly one proximal-package-index entry "
            "in pyproject.toml."
        )

    return matching_urls[0]


def main() -> int:
    args = build_parser().parse_args()
    project = load_project()

    if args.field == "core-version":
        print(read_core_version(project=project), end="")
        return 0

    print(read_package_index_url(project=project), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
