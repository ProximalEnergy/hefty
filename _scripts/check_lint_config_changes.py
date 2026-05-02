from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

FULL_FILE_CONFIGS = {
    "web-app/knip.json": "web-app/knip.json",
    "web-app/.oxlintrc.json": "web-app/.oxlintrc.json",
    "web-app/tsconfig.json": "web-app/tsconfig.json",
    "web-app/tsconfig.node.json": "web-app/tsconfig.node.json",
}

PACKAGE_JSON_KEYS = (
    "scripts.lint",
    "scripts.lint:github",
    "scripts.typecheck",
    "scripts.prettier",
    "scripts.prettier:check",
    "scripts.knip",
    "scripts.check",
    "prettier",
)

MISSING = object()


def run_git(
    *,
    args: list[str],
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=check,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def resolve_base_ref(*, requested_base_ref: str | None) -> str | None:
    if requested_base_ref:
        candidates = (requested_base_ref,)
    else:
        candidates = ("dev", "origin/dev")

    for candidate in candidates:
        result = run_git(
            args=["rev-parse", "--verify", "--quiet", f"{candidate}^{{commit}}"],
        )
        if result.returncode == 0:
            return candidate

    return None


def read_base_file(*, base_ref: str, path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{base_ref}:{path}"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if result.returncode == 0:
        return result.stdout
    return None


def read_current_file(*, path: str) -> bytes | None:
    current_path = REPO_ROOT / path
    if not current_path.exists():
        return None
    return current_path.read_bytes()


def load_toml_config(*, content: bytes | None, path: str) -> dict[str, Any]:
    if content is None:
        return {}
    try:
        return tomllib.loads(content.decode())
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"{path} is not valid TOML: {exc}") from exc


def load_json_config(*, content: bytes | None, path: str) -> dict[str, Any]:
    if content is None:
        return {}
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def get_nested_value(*, data: dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def package_lint_config(*, content: bytes | None) -> dict[str, Any]:
    package_json = load_json_config(content=content, path="web-app/package.json")
    return {
        key: get_nested_value(data=package_json, dotted_key=key)
        for key in PACKAGE_JSON_KEYS
    }


def pyproject_lint_config(*, content: bytes | None) -> dict[str, Any]:
    pyproject = load_toml_config(content=content, path="pyproject.toml")
    tool = pyproject.get("tool", {})
    if not isinstance(tool, dict):
        tool = {}
    return {
        "tool.ruff": tool.get("ruff", MISSING),
        "tool.mypy": tool.get("mypy", MISSING),
    }


def full_file_changed(*, base_ref: str, path: str) -> bool:
    return read_base_file(base_ref=base_ref, path=path) != read_current_file(path=path)


def protected_config_changes(*, base_ref: str) -> list[str]:
    changes: list[str] = []

    for path, label in FULL_FILE_CONFIGS.items():
        if full_file_changed(base_ref=base_ref, path=path):
            changes.append(label)

    base_pyproject = read_base_file(base_ref=base_ref, path="pyproject.toml")
    current_pyproject = read_current_file(path="pyproject.toml")
    if pyproject_lint_config(content=base_pyproject) != pyproject_lint_config(
        content=current_pyproject,
    ):
        changes.append("pyproject.toml [tool.ruff]/[tool.mypy]")

    base_package = read_base_file(base_ref=base_ref, path="web-app/package.json")
    current_package = read_current_file(path="web-app/package.json")
    if package_lint_config(content=base_package) != package_lint_config(
        content=current_package,
    ):
        changes.append("web-app/package.json lint/prettier script config")

    return changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail when protected lint config differs from dev.",
    )
    parser.add_argument(
        "--base-ref",
        help="Base ref to compare against. Defaults to dev, then origin/dev.",
    )
    return parser.parse_args()


def check_lint_config_changes() -> int:
    args = parse_args()
    base_ref = resolve_base_ref(requested_base_ref=args.base_ref)
    if base_ref is None:
        requested = args.base_ref or "dev/origin/dev"
        print(f"Base ref not found: {requested}", file=sys.stderr)
        return 2

    try:
        changes = protected_config_changes(base_ref=base_ref)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not changes:
        print(f"No protected lint config changes detected vs {base_ref}.")
        return 0

    print(f"Protected lint config changed vs {base_ref}:", file=sys.stderr)
    for change in changes:
        print(f"- {change}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(check_lint_config_changes())
