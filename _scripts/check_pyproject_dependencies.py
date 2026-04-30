from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


def dependency_name(*, requirement: str) -> str:
    base = requirement.split(";", 1)[0].strip()
    if " @" in base:
        base = base.split(" @", 1)[0].strip()
    base = base.split("[", 1)[0].strip()
    if " " in base:
        base = base.split()[0]
    match = NAME_RE.match(base)
    if match:
        base = match.group(0)
    return base.lower().replace("_", "-")


def dependency_sort_key(*, requirement: str) -> tuple[str, str]:
    return (dependency_name(requirement=requirement), requirement.lower())


def check_list(
    *,
    dependencies: list[str],
    label: str,
    errors: list[str],
    allow_unbounded: set[str],
) -> None:
    if not dependencies:
        return

    names = [dependency_name(requirement=dep) for dep in dependencies]
    seen: dict[str, str] = {}
    duplicates: dict[str, list[str]] = {}
    for dep, name in zip(dependencies, names, strict=True):
        if name in seen:
            duplicates.setdefault(name, [seen[name]]).append(dep)
        else:
            seen[name] = dep

    for name, entries in duplicates.items():
        joined = ", ".join(entries)
        errors.append(f"{label} has duplicate entries for {name}: {joined}")

    expected = sorted(
        dependencies, key=lambda dep: dependency_sort_key(requirement=dep)
    )
    if dependencies != expected:
        ordered = ", ".join(expected)
        errors.append(f"{label} is not sorted. Expected: {ordered}")

    for requirement in dependencies:
        if not has_upper_bound(
            requirement=requirement,
            allow_unbounded=allow_unbounded,
        ):
            errors.append(f"{label} has unbounded dependency: {requirement}")


def has_upper_bound(
    *,
    requirement: str,
    allow_unbounded: set[str],
) -> bool:
    base = requirement.split(";", 1)[0].strip()
    if " @" in base:
        return True

    name = dependency_name(requirement=requirement)
    if name in allow_unbounded:
        return True

    match = re.search(r"[<>=!~]", base)
    if not match:
        return False

    specifiers = [
        spec.strip() for spec in base[match.start() :].split(",") if spec.strip()
    ]
    if any(spec.startswith("~=") for spec in specifiers):
        return True

    if any(spec.startswith("<") for spec in specifiers):
        return True

    for spec in specifiers:
        if spec.startswith("==="):
            value = spec[3:].strip()
            return "*" not in value
        if spec.startswith("=="):
            value = spec[2:].strip()
            return "*" not in value

    return False


def managed_dependency_names(
    *,
    dependencies: object,
    allow_unbounded: set[str],
) -> set[str]:
    if not isinstance(dependencies, list):
        return set()

    managed_names: set[str] = set()
    for requirement in dependencies:
        if not isinstance(requirement, str):
            continue
        if not has_upper_bound(
            requirement=requirement,
            allow_unbounded=allow_unbounded,
        ):
            continue
        managed_names.add(dependency_name(requirement=requirement))
    return managed_names


def is_bare_requirement(*, requirement: str) -> bool:
    stripped = requirement.strip()
    if ";" in stripped:
        return False
    if " @" in stripped:
        return False
    if "[" in stripped or "]" in stripped:
        return False
    return NAME_RE.fullmatch(stripped) is not None


def check_pyproject(
    *,
    path: Path,
    errors: list[str],
    extra_allow_unbounded: set[str] | None = None,
    extra_group_allow_unbounded: dict[str, set[str]] | None = None,
) -> None:
    try:
        with path.open("rb") as file_handle:
            data = tomllib.load(file_handle)
    except FileNotFoundError:
        errors.append(f"{path} not found")
        return
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"{path} is not valid TOML: {exc}")
        return

    project = data.get("project", {})
    tool = data.get("tool", {})
    uv = tool.get("uv", {})
    sources = uv.get("sources", {})
    allow_unbounded: set[str] = set(extra_allow_unbounded or [])
    if isinstance(sources, dict):
        allow_unbounded.update(name.lower().replace("_", "-") for name in sources)
    dependencies = project.get("dependencies", [])
    if isinstance(dependencies, list):
        check_list(
            dependencies=dependencies,
            label=f"{path} [project.dependencies]",
            errors=errors,
            allow_unbounded=allow_unbounded,
        )
        if path.as_posix().endswith("core/pyproject.toml"):
            for requirement in dependencies:
                name = dependency_name(requirement=requirement)
                if name not in allow_unbounded:
                    continue
                if is_bare_requirement(requirement=requirement):
                    continue
                errors.append(
                    f"{path} [project.dependencies] must keep root-managed "
                    f"dependency blank: {requirement}"
                )
    elif dependencies:
        errors.append(f"{path} [project.dependencies] must be a list")

    groups = data.get("dependency-groups", {})
    if isinstance(groups, dict):
        for group_name, group_deps in groups.items():
            if not isinstance(group_deps, list):
                errors.append(f"{path} [dependency-groups.{group_name}] must be a list")
                continue
            group_allow_unbounded = set(allow_unbounded)
            if extra_group_allow_unbounded is not None:
                group_allow_unbounded.update(
                    extra_group_allow_unbounded.get(group_name, set())
                )
            check_list(
                dependencies=group_deps,
                label=f"{path} [dependency-groups.{group_name}]",
                errors=errors,
                allow_unbounded=group_allow_unbounded,
            )
    elif groups:
        errors.append(f"{path} [dependency-groups] must be a table")


def discover_pyprojects(*, root: Path) -> list[Path]:
    try:
        output = subprocess.check_output(
            [
                "git",
                "-C",
                str(root),
                "grep",
                "--untracked",
                "-l",
                "",
                "--",
                "pyproject.toml",
                "**/pyproject.toml",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.SubprocessError:
        return discover_pyprojects_via_walk(root=root)

    paths = [root / rel for rel in output.splitlines() if rel]
    return sorted(paths)


def discover_pyprojects_via_walk(*, root: Path) -> list[Path]:
    paths: list[Path] = []
    for current_root, dir_names, file_names in root.walk(top_down=True):
        dir_names[:] = [
            dir_name for dir_name in dir_names if dir_name not in SKIP_DIRS
        ]
        if "pyproject.toml" in file_names:
            paths.append(current_root / "pyproject.toml")
    return sorted(paths)


def workspace_root_dependencies(
    *,
    root: Path,
) -> tuple[set[str], dict[str, set[str]]]:
    root_pyproject = root / "pyproject.toml"
    try:
        with root_pyproject.open("rb") as fh:
            data = tomllib.load(fh)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return set(), {}

    workspace = data.get("tool", {}).get("uv", {}).get("workspace", {})
    if not workspace:
        return set(), {}

    uv = data.get("tool", {}).get("uv", {})
    sources = uv.get("sources", {})
    allow_unbounded: set[str] = set()
    if isinstance(sources, dict):
        allow_unbounded.update(name.lower().replace("_", "-") for name in sources)

    managed_dependencies = managed_dependency_names(
        dependencies=data.get("project", {}).get("dependencies", []),
        allow_unbounded=allow_unbounded,
    )

    managed_groups: dict[str, set[str]] = {}
    groups = data.get("dependency-groups", {})
    if isinstance(groups, dict):
        for group_name, group_deps in groups.items():
            managed_groups[group_name] = managed_dependency_names(
                dependencies=group_deps,
                allow_unbounded=allow_unbounded,
            )

    return managed_dependencies, managed_groups


def workspace_root_bounded_dependencies(*, root: Path) -> set[str]:
    managed_dependencies, _ = workspace_root_dependencies(root=root)
    return managed_dependencies


def check_pyproject_dependencies() -> int:
    root = Path.cwd()
    root_pyproject = root / "pyproject.toml"
    root_bounded, root_group_bounded = workspace_root_dependencies(root=root)
    errors: list[str] = []
    for path in discover_pyprojects(root=root):
        extra_allow_unbounded = None
        extra_group_allow_unbounded = None
        if path != root_pyproject:
            extra_allow_unbounded = root_bounded
            extra_group_allow_unbounded = root_group_bounded
        check_pyproject(
            path=path,
            errors=errors,
            extra_allow_unbounded=extra_allow_unbounded,
            extra_group_allow_unbounded=extra_group_allow_unbounded,
        )

    if errors:
        print("Pyproject dependency checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Pyproject dependency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(check_pyproject_dependencies())
