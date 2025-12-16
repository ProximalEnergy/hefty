#!/usr/bin/env python3
"""
Script to automatically update release notes when running database migrations.

This script will:
1. Read the current version from pyproject.toml
2. Determine the appropriate release file (e.g., v0.2.x.md)
3. Add a new entry with the current version and migration message
4. Handle version increments and new release files as needed
"""

import argparse
import re
import tomllib
from pathlib import Path


class ReleaseUpdater:
    def __init__(self, project_root: str = "."):
        """TODO: add description.

        Args:
            self: TODO: describe.
            project_root: TODO: describe.
        """
        self.project_root = Path(project_root)
        self.releases_dir = self.project_root / "_docs" / "releases"
        self.pyproject_path = self.project_root / "pyproject.toml"

    def get_current_version(self) -> str:
        """Get the current version from pyproject.toml.

        Args:
            self: TODO: describe.
        """
        if not self.pyproject_path.exists():
            raise FileNotFoundError(
                f"pyproject.toml not found at {self.pyproject_path}"
            )

        with open(self.pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)

        return pyproject_data["project"]["version"]

    def get_release_file_path(self, version: str) -> Path:
        """Determine the appropriate release file for a given version.

        Args:
            self: TODO: describe.
            version: TODO: describe.
        """
        # Extract major and minor version (e.g., "0.2.23" -> "0.2")
        major_minor = ".".join(version.split(".")[:2])
        return self.releases_dir / f"v{major_minor}.x.md"

    def version_exists_in_file(self, file_path: Path, version: str) -> bool:
        """Check if a version already exists in the release file.

        Args:
            self: TODO: describe.
            file_path: TODO: describe.
            version: TODO: describe.
        """
        if not file_path.exists():
            return False

        with open(file_path) as f:
            content = f.read()

        version_pattern = rf"^# v{re.escape(version)}$"
        return bool(re.search(version_pattern, content, re.MULTILINE))

    def add_release_entry(self, version: str, message: str) -> None:
        """Add a new release entry to the appropriate file.

        Args:
            self: TODO: describe.
            version: TODO: describe.
            message: TODO: describe.
        """
        release_file = self.get_release_file_path(version)

        # Check if version already exists
        if self.version_exists_in_file(release_file, version):
            print(f"Version v{version} already exists in {release_file.name}")  # noqa: T201
            return

        # Ensure releases directory exists
        self.releases_dir.mkdir(parents=True, exist_ok=True)

        # Create new entry
        new_entry = f"# v{version}\n\n- {message}\n\n"

        if release_file.exists():
            # Read existing content
            with open(release_file) as f:
                existing_content = f.read()

            # Find the right place to insert the new version
            # We want to insert in descending version order
            lines = existing_content.split("\n")
            insert_index = None

            # Find where to insert based on version comparison
            for i, line in enumerate(lines):
                if line.startswith("# v"):
                    existing_version = line[3:]  # Remove "# v"
                    if self._compare_versions(version, existing_version) > 0:
                        # New version is greater, insert before this line
                        insert_index = i
                        break

            # Insert the new entry
            if insert_index is None or insert_index == 0:
                # Insert at the beginning (new version is greater than all)
                new_content = new_entry + existing_content
            else:
                # Insert at the found position
                lines.insert(insert_index, f"# v{version}")
                lines.insert(insert_index + 1, "")
                lines.insert(insert_index + 2, f"- {message}")
                lines.insert(insert_index + 3, "")

                new_content = "\n".join(lines)
        else:
            # Create new file
            new_content = new_entry

        # Write the updated content
        with open(release_file, "w") as f:
            f.write(new_content)

        print(f"✓ Added v{version} to {release_file.name}: {message}")  # noqa: T201

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings.
                Returns: 1 if v1 > v2, -1 if v1 < v2, 0 if equal

        Args:
            self: TODO: describe.
            v1: TODO: describe.
            v2: TODO: describe.
        """

        def version_tuple(v):
            """TODO: add description.

            Args:
                v: TODO: describe.
            """
            return tuple(map(int, v.split(".")))

        tuple1 = version_tuple(v1)
        tuple2 = version_tuple(v2)

        if tuple1 > tuple2:
            return 1
        elif tuple1 < tuple2:
            return -1
        else:
            return 0

    def run(self, message: str) -> None:
        """Main method to update releases with the given message.

        Args:
            self: TODO: describe.
            message: TODO: describe.
        """
        try:
            current_version = self.get_current_version()
            self.add_release_entry(current_version, message)
        except Exception as e:
            print(f"Error updating releases: {e}")  # noqa: T201
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Update release notes with a new migration message"
    )
    parser.add_argument(
        "message", help="The migration message to add to the release notes"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Path to the project root directory (default: current directory)",
    )

    args = parser.parse_args()

    try:
        updater = ReleaseUpdater(args.project_root)
        updater.run(args.message)
        return 0
    except Exception as e:
        print(f"Failed to update releases: {e}")  # noqa: T201
        return 1


if __name__ == "__main__":
    exit(main())
