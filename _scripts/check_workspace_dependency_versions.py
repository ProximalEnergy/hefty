# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")
VERSION_SPECIFIER_RE = re.compile(r"[<>=!~]")


def dependency_name(*, requirement: str) -> str:
    base = requirement.split(";", 1)[0].strip()
    if " @" in base:
        base = base.split(" @", 1)[0].strip()
    base = base.split("[", 1)[0].strip()
    if " " in base:
        base = base.split()[0]
    match = NAME_RE.match(base)
    if match is not None:
        base = match.group(0)
    return base.lower().replace("_", "-")


def requirement_is_versioned(*, requirement: str) -> bool:
    base = requirement.split(";", 1)[0].strip()
    return " @" in base or VERSION_SPECIFIER_RE.search(base) is not None


def load_toml(*, path: Path, errors: list[str]) -> dict[str, object]:
    try:
        with path.open("rb") as file_handle:
            return tomllib.load(file_handle)
    except FileNotFoundError:
        errors.append(f"{path.as_posix()} not found")
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"{path.as_posix()} is not valid TOML: {exc}")
    return {}


def dependency_lists(
    *,
    data: dict[str, object],
    path: Path,
    errors: list[str],
) -> list[tuple[str, list[object]]]:
    lists: list[tuple[str, list[object]]] = []
    project = data.get("project", {})
    if isinstance(project, dict):
        dependencies = project.get("dependencies", [])
        if isinstance(dependencies, list):
            lists.append(("[project.dependencies]", dependencies))
        elif dependencies:
            errors.append(f"{path.as_posix()} [project.dependencies] must be a list")

    groups = data.get("dependency-groups", {})
    if isinstance(groups, dict):
        for group_name, dependencies in groups.items():
            label = f"[dependency-groups.{group_name}]"
            if isinstance(dependencies, list):
                lists.append((label, dependencies))
            else:
                errors.append(f"{path.as_posix()} {label} must be a list")
    elif groups:
        errors.append(f"{path.as_posix()} [dependency-groups] must be a table")

    return lists


def root_versioned_dependency_names(
    *,
    root_pyproject: dict[str, object],
    root_path: Path,
    errors: list[str],
) -> set[str]:
    names: set[str] = set()
    for _, dependencies in dependency_lists(
        data=root_pyproject,
        path=root_path,
        errors=errors,
    ):
        for requirement in dependencies:
            if not isinstance(requirement, str):
                continue
            if requirement_is_versioned(requirement=requirement):
                names.add(dependency_name(requirement=requirement))
    return names


def workspace_members(
    *,
    root_pyproject: dict[str, object],
    root: Path,
    errors: list[str],
) -> list[Path]:
    tool = root_pyproject.get("tool", {})
    if not isinstance(tool, dict):
        errors.append("pyproject.toml [tool] must be a table")
        return []

    uv = tool.get("uv", {})
    if not isinstance(uv, dict):
        errors.append("pyproject.toml [tool.uv] must be a table")
        return []

    workspace = uv.get("workspace", {})
    if not isinstance(workspace, dict):
        errors.append("pyproject.toml [tool.uv.workspace] must be a table")
        return []

    members = workspace.get("members", [])
    if not isinstance(members, list):
        errors.append("pyproject.toml [tool.uv.workspace.members] must be a list")
        return []

    member_paths: list[Path] = []
    for member in members:
        if not isinstance(member, str):
            errors.append("pyproject.toml workspace member must be a string")
            continue
        matches = sorted(root.glob(member))
        if matches:
            member_paths.extend(path for path in matches if path.is_dir())
        else:
            member_paths.append(root / member)
    return sorted(set(member_paths))


def discover_pyprojects_with_ripgrep(*, root: Path, errors: list[str]) -> set[Path]:
    try:
        result = subprocess.run(
            ["rg", "--files", "-g", "pyproject.toml"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        errors.append(f"failed to discover pyproject.toml files with rg: {exc}")
        return set()

    return {
        root / line
        for line in result.stdout.splitlines()
        if line.strip()
    }


def check_workspace_dependency_versions() -> int:
    root = Path.cwd()
    root_path = root / "pyproject.toml"
    errors: list[str] = []
    discovered_pyprojects = discover_pyprojects_with_ripgrep(
        root=root,
        errors=errors,
    )
    root_pyproject = load_toml(path=root_path, errors=errors)
    root_names = root_versioned_dependency_names(
        root_pyproject=root_pyproject,
        root_path=root_path,
        errors=errors,
    )

    for member_path in workspace_members(
        root_pyproject=root_pyproject,
        root=root,
        errors=errors,
    ):
        pyproject_path = member_path / "pyproject.toml"
        if discovered_pyprojects and pyproject_path not in discovered_pyprojects:
            errors.append(f"{pyproject_path.as_posix()} not found by rg")
            continue
        member_pyproject = load_toml(path=pyproject_path, errors=errors)
        relative_path = pyproject_path.relative_to(root)
        for label, dependencies in dependency_lists(
            data=member_pyproject,
            path=relative_path,
            errors=errors,
        ):
            for requirement in dependencies:
                if not isinstance(requirement, str):
                    continue
                name = dependency_name(requirement=requirement)
                if name not in root_names:
                    continue
                if not requirement_is_versioned(requirement=requirement):
                    continue
                errors.append(
                    f"{relative_path.as_posix()} {label} versions "
                    f"root-managed dependency: {requirement}"
                )

    if errors:
        print("Workspace dependency version check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Workspace dependency version check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(check_workspace_dependency_versions())
