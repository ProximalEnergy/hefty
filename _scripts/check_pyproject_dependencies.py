from __future__ import annotations

from pathlib import Path
import re
import sys
import tomllib

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


def sort_key(*, requirement: str) -> tuple[str, str]:
    return (dependency_name(requirement=requirement), requirement.lower())


def check_list(
    *,
    dependencies: list[str],
    label: str,
    errors: list[str],
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

    expected = sorted(dependencies, key=lambda dep: sort_key(requirement=dep))
    if dependencies != expected:
        ordered = ", ".join(expected)
        errors.append(f"{label} is not sorted. Expected: {ordered}")


def check_pyproject(*, path: Path, errors: list[str]) -> None:
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        errors.append(f"{path} not found")
        return

    try:
        data = tomllib.loads(content.decode())
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"{path} is not valid TOML: {exc}")
        return

    project = data.get("project", {})
    dependencies = project.get("dependencies", [])
    if isinstance(dependencies, list):
        check_list(
            dependencies=dependencies,
            label=f"{path} [project.dependencies]",
            errors=errors,
        )
    elif dependencies:
        errors.append(f"{path} [project.dependencies] must be a list")

    groups = data.get("dependency-groups", {})
    if isinstance(groups, dict):
        for group_name, group_deps in groups.items():
            if not isinstance(group_deps, list):
                errors.append(f"{path} [dependency-groups.{group_name}] must be a list")
                continue
            check_list(
                dependencies=group_deps,
                label=f"{path} [dependency-groups.{group_name}]",
                errors=errors,
            )
    elif groups:
        errors.append(f"{path} [dependency-groups] must be a table")


def discover_pyprojects(*, root: Path) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("pyproject.toml"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        paths.append(path)
    return sorted(paths)


def main() -> int:
    errors: list[str] = []
    for path in discover_pyprojects(root=Path.cwd()):
        check_pyproject(path=path, errors=errors)

    if errors:
        print("Pyproject dependency checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Pyproject dependency checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
