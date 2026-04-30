#!/usr/bin/env python3

from __future__ import annotations

import argparse
import email
import re
import sys
import tomllib
import zipfile
from pathlib import Path

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


def load_pyproject(*, path: Path) -> dict:
    with path.open("rb") as file_handle:
        return tomllib.load(file_handle)


def load_dependencies(*, path: Path) -> list[str]:
    data = load_pyproject(path=path)
    dependencies = data.get("project", {}).get("dependencies", [])
    if not isinstance(dependencies, list):
        raise TypeError(f"{path} project.dependencies must be a list")
    if not all(isinstance(dep, str) for dep in dependencies):
        raise TypeError(f"{path} project.dependencies must contain only strings")
    return dependencies


def dependency_map(*, requirements: list[str]) -> dict[str, str]:
    names: dict[str, str] = {}
    for requirement in requirements:
        name = dependency_name(requirement=requirement)
        if name in names:
            raise ValueError(
                f"Duplicate dependency entry for {name}: "
                f"{names[name]}, {requirement}"
            )
        names[name] = requirement
    return names


def requirement_specifiers(*, requirement: str) -> tuple[str, tuple[str, ...]]:
    base = requirement.split(";", 1)[0].strip()
    match = NAME_RE.match(base)
    if match is None:
        raise ValueError(f"Could not parse dependency name from {requirement!r}")
    name = match.group(0).lower().replace("_", "-")
    remainder = base[match.end() :].strip()
    if remainder.startswith("(") and remainder.endswith(")"):
        remainder = remainder[1:-1].strip()
    if not remainder:
        return (name, ())
    specifiers = tuple(
        sorted(spec.strip() for spec in remainder.split(",") if spec.strip())
    )
    return (name, specifiers)


def is_bare_requirement(*, requirement: str) -> bool:
    stripped = requirement.strip()
    if ";" in stripped:
        return False
    if " @" in stripped:
        return False
    if "[" in stripped or "]" in stripped:
        return False
    return NAME_RE.fullmatch(stripped) is not None


def expected_root_requirements(
    *,
    root_pyproject: Path,
    core_pyproject: Path,
) -> list[str]:
    root_dependencies = load_dependencies(path=root_pyproject)
    core_dependencies = load_dependencies(path=core_pyproject)
    root_by_name = dependency_map(requirements=root_dependencies)
    expected: list[str] = []

    for requirement in core_dependencies:
        if not is_bare_requirement(requirement=requirement):
            raise ValueError(
                "Committed core dependency entries must stay blank for "
                f"root-managed publish deps: {requirement}"
            )
        name = dependency_name(requirement=requirement)
        if name not in root_by_name:
            raise ValueError(
                f"Missing root dependency for core publish dependency: {name}"
            )
        expected.append(root_by_name[name])

    return expected


def format_dependency_block(*, requirements: list[str]) -> str:
    rendered = "\n".join(f'    "{requirement}",' for requirement in requirements)
    return f"dependencies = [\n{rendered}\n]"


def replace_project_dependencies(*, text: str, requirements: list[str]) -> str:
    pattern = re.compile(
        r"(?ms)(^\[project\]\n.*?^)dependencies = \[\n.*?^\]",
    )
    replacement = "\\1" + format_dependency_block(requirements=requirements)
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise ValueError("Could not replace project.dependencies block")
    return updated


def replace_version(*, text: str, version: str) -> str:
    updated, count = re.subn(
        r'(?m)^version = "[^"]+"$',
        f'version = "{version}"',
        text,
        count=1,
    )
    if count != 1:
        raise ValueError("Could not replace project version")
    return updated


def inject_publish_metadata(
    *,
    root_pyproject: Path,
    core_pyproject: Path,
    build_pyproject: Path,
    version: str,
) -> None:
    expected = expected_root_requirements(
        root_pyproject=root_pyproject,
        core_pyproject=core_pyproject,
    )
    content = build_pyproject.read_text(encoding="utf-8")
    content = replace_project_dependencies(text=content, requirements=expected)
    content = replace_version(text=content, version=version)
    build_pyproject.write_text(content, encoding="utf-8")


def metadata_requirements(*, wheel_path: Path) -> list[str]:
    with zipfile.ZipFile(wheel_path) as wheel_file:
        metadata_name = next(
            (
                name
                for name in wheel_file.namelist()
                if name.endswith(".dist-info/METADATA")
            ),
            None,
        )
        if metadata_name is None:
            raise ValueError(f"No METADATA file found in {wheel_path}")
        payload = wheel_file.read(metadata_name).decode("utf-8")

    message = email.message_from_string(payload)
    return message.get_all("Requires-Dist", [])


def verify_wheel(
    *,
    root_pyproject: Path,
    core_pyproject: Path,
    wheel_path: Path,
) -> None:
    expected = expected_root_requirements(
        root_pyproject=root_pyproject,
        core_pyproject=core_pyproject,
    )
    expected_by_name = {
        name: specifiers
        for name, specifiers in (
            requirement_specifiers(requirement=r) for r in expected
        )
    }
    actual_by_name = {
        name: specifiers
        for name, specifiers in (
            requirement_specifiers(requirement=r)
            for r in metadata_requirements(wheel_path=wheel_path)
        )
    }

    missing = sorted(set(expected_by_name) - set(actual_by_name))
    mismatched = sorted(
        name for name, specifiers in expected_by_name.items()
        if actual_by_name.get(name) != specifiers
    )

    errors: list[str] = []
    if missing:
        errors.append(f"Missing Requires-Dist entries: {', '.join(missing)}")
    for name in mismatched:
        errors.append(
            f"{name} expected specifiers {expected_by_name[name]!r} but found "
            f"{actual_by_name.get(name)!r}"
        )
    if errors:
        raise ValueError(
            f"Wheel metadata did not match injected root pins for {wheel_path}:\n"
            + "\n".join(errors)
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and validate the publish-time core artifact.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inject = subparsers.add_parser(
        "inject",
        help="Inject root-managed dependency pins into a temp core pyproject.",
    )
    inject.add_argument("--root-pyproject", required=True)
    inject.add_argument("--core-pyproject", required=True)
    inject.add_argument("--build-pyproject", required=True)
    inject.add_argument("--version", required=True)

    verify = subparsers.add_parser(
        "verify-wheel",
        help="Verify the built wheel contains the injected root-managed pins.",
    )
    verify.add_argument("--root-pyproject", required=True)
    verify.add_argument("--core-pyproject", required=True)
    verify.add_argument("--wheel", required=True)

    return parser.parse_args()


def prepare_core_publish_artifact() -> int:
    args = parse_args()

    try:
        if args.command == "inject":
            inject_publish_metadata(
                root_pyproject=Path(args.root_pyproject),
                core_pyproject=Path(args.core_pyproject),
                build_pyproject=Path(args.build_pyproject),
                version=args.version,
            )
        else:
            verify_wheel(
                root_pyproject=Path(args.root_pyproject),
                core_pyproject=Path(args.core_pyproject),
                wheel_path=Path(args.wheel),
            )
    except (FileNotFoundError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(prepare_core_publish_artifact())
