#!/usr/bin/env python3

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from packaging.version import Version


def load_toml(file_path: Path) -> dict[str, Any]:
    with file_path.open("rb") as file_handle:
        return tomllib.load(file_handle)


def get_pyproject_core_version(project_root: Path) -> Version:
    pyproject_path = project_root / "pyproject.toml"
    project = load_toml(pyproject_path)
    dependencies = project.get("project", {}).get("dependencies", [])
    
    # Looking for "core==x.y.z" (including beta/rc suffixes)
    for dep in dependencies:
        # Strip potential comments
        clean_dep = dep.split("#")[0].strip()
        if clean_dep.startswith("core"):
            # Match "core" followed by "==" and then the version string.
            # PEP 440 versions can contain alphanumeric characters and .-_+
            match = re.fullmatch(r"core\s*==\s*([A-Za-z0-9][A-Za-z0-9._+-]*)", clean_dep)
            if match:
                return Version(match.group(1))
    
    raise SystemExit(f"Could not find pinned core dependency in {pyproject_path}")


def get_uv_lock_core_version(project_root: Path) -> Version:
    lock_path = project_root / "uv.lock"
    lock_data = load_toml(lock_path)
    packages = lock_data.get("package", [])
    
    for pkg in packages:
        if pkg.get("name") == "core":
            version_str = pkg.get("version")
            if version_str:
                return Version(version_str)
    
    raise SystemExit(f"Could not find core package in {lock_path}")


def main() -> int:
    project_root = Path(__file__).parent.parent
    
    try:
        pyproject_version = get_pyproject_core_version(project_root)
        uv_lock_version = get_uv_lock_core_version(project_root)
    except Exception as e:
        print(f"ERROR: Failed to parse versions: {e}")
        return 1
    
    if pyproject_version != uv_lock_version:
        if pyproject_version.is_prerelease:
            print(f"SUCCESS: 'core' package version {pyproject_version} is a pre-release; "
                  f"skipping strict parity check against uv.lock version {uv_lock_version}.")
            return 0
        print(f"ERROR: Pin parity check failed for 'core' package!")
        print(f"  pyproject.toml: {pyproject_version}")
        print(f"  uv.lock:        {uv_lock_version}")
        return 1
    
    print(f"SUCCESS: 'core' package version {pyproject_version} matches in both files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
