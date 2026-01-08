#!/usr/bin/env python3
"""
Script to clean up Alembic migration files by removing the @for_each_project_schema
decorator and schema parameter when "operational" is the only schema being used.

This script will:
1. Find all migration files that use @for_each_project_schema
2. Analyze if they only reference the "operational" schema
3. Remove the decorator and schema parameter, hardcoding schema="operational"
4. Remove the import for for_each_project_schema if no longer needed
"""

import argparse
import re
from pathlib import Path

# Schemas that should be cleaned when only hardcoded references are found
SCHEMAS_TO_CLEAN = {"operational", "admin"}


class MigrationCleaner:
    def __init__(self, migrations_dir: str):
        """TODO: add description.

        Args:
            migrations_dir: TODO: describe.
        """
        self.migrations_dir = Path(migrations_dir)

    def find_migration_files(self) -> list[Path]:
        """Find all Python migration files in the versions directory."""
        versions_dir = self.migrations_dir / "versions"
        if not versions_dir.exists():
            raise FileNotFoundError(f"Versions directory not found: {versions_dir}")

        return list(versions_dir.glob("*.py"))

    def analyze_file(self, file_path: Path) -> tuple[bool, bool, str]:
        """Analyze a migration file to determine:
                1. If it uses @for_each_project_schema decorator
                2. If it should be cleaned (incorrectly uses decorator)
                3. Reason for the decision

        Args:
            file_path: TODO: describe.
        """
        with open(file_path) as f:
            content = f.read()

        # Check if file uses the decorator
        uses_decorator = "@for_each_project_schema" in content
        if not uses_decorator:
            return False, False, "no decorator"

        # Analyze the content to determine if it should be cleaned
        should_clean, reason = self._should_clean_migration(content)
        return uses_decorator, should_clean, reason

    def _should_clean_migration(self, content: str) -> tuple[bool, str]:
        """Determine if a migration should be cleaned based on its content.

                A migration should be cleaned if:
                1. It uses @for_each_project_schema decorator
                2. BUT the only schema referenced is "operational" (hardcoded)
                3. AND it never uses the schema parameter (schema=schema)

                Returns: (should_clean, reason)

        Args:
            content: TODO: describe.
        """
        # Count schema references (both single and double quotes)
        schema_param_count = len(re.findall(r"schema=schema", content))

        # Look for all hardcoded schema references
        all_schema_matches = re.findall(r"schema=['\"]([^'\"]+)['\"]", content)
        unique_schemas = set(all_schema_matches)

        # Count schemas that should be cleaned
        cleanable_schemas = unique_schemas.intersection(SCHEMAS_TO_CLEAN)
        other_schemas = unique_schemas - SCHEMAS_TO_CLEAN

        # Check if only cleanable schemas are used (hardcoded) and no schema parameter
        if (
            len(cleanable_schemas) > 0
            and schema_param_count == 0
            and len(other_schemas) == 0
        ):
            schema_list = ", ".join(f"'{s}'" for s in sorted(cleanable_schemas))
            total_count = len(all_schema_matches)
            return (
                True,
                f"only uses hardcoded schema(s) {schema_list} ({total_count} "
                "times), should not use for_each_project decorator",
            )

        # Check if migration uses schema parameter - these are likely correct
        if schema_param_count > 0:
            # Check if it also has FK references to cleanable schemas
            has_cleanable_fk_refs = any(
                f'referent_schema="{schema}"' in content for schema in SCHEMAS_TO_CLEAN
            )
            if has_cleanable_fk_refs:
                return (
                    False,
                    "uses schema parameter for project tables with FK to "
                    "cleanable schemas",
                )
            else:
                return (False, "uses schema parameter for operations (likely correct)")

        # Default to not cleaning
        return False, "no clear indication it should be cleaned"

    def clean_file(self, file_path: Path) -> bool:
        """Clean a migration file by removing decorator and schema parameter.
                Returns True if file was modified.

        Args:
            file_path: TODO: describe.
        """
        with open(file_path) as f:
            content = f.read()

        original_content = content

        # Remove the import line for for_each_project_schema
        content = re.sub(
            r"^from _alembic_migrations\.tenant import for_each_project_schema\n",
            "",
            content,
            flags=re.MULTILINE,
        )

        # Also handle the case where it's imported with other imports
        content = re.sub(
            r"from _alembic_migrations\.tenant import "
            r"([^,\n]*,\s*)?for_each_project_schema(,\s*[^,\n]*)?",
            lambda m: f"from _alembic_migrations.tenant import "
            f"{m.group(1) or ''}{m.group(2) or ''}".replace("import ,", "import")
            .replace(", ,", ",")
            .strip()
            .rstrip(","),
            content,
        )

        # Remove empty import lines
        content = re.sub(
            r"^from _alembic_migrations\.tenant import\s*$",
            "",
            content,
            flags=re.MULTILINE,
        )

        # Remove @for_each_project_schema decorator
        content = re.sub(
            r"^@for_each_project_schema\n", "", content, flags=re.MULTILINE
        )

        # Remove schema parameter from function definitions
        content = re.sub(
            r"^def (upgrade|downgrade)\(schema: str\) -> None:",
            r"def \1() -> None:",
            content,
            flags=re.MULTILINE,
        )

        # Replace schema=schema with schema="operational" (default to operational)
        content = re.sub(r"schema=schema", 'schema="operational"', content)

        # Clean up extra blank lines that might have been created
        content = re.sub(r"\n\n\n+", "\n\n", content)

        if content != original_content:
            with open(file_path, "w") as f:
                f.write(content)
            return True

        return False

    def run(self, dry_run: bool = False, latest_only: bool = False) -> None:
        """
        Run the cleaning process on all migration files.

        Args:
            dry_run: Show what would be cleaned without making changes
            latest_only: Only process the newest migration file and skip confirmation
        """
        migration_files = self.find_migration_files()

        if latest_only:
            # Sort by filename (which includes timestamp) and get the latest
            migration_files = sorted(migration_files, key=lambda x: x.name)
            if migration_files:
                migration_files = [migration_files[-1]]  # Only the latest file
                print(f"Processing latest migration file: {migration_files[0].name}")  # noqa: T201
            else:
                print("No migration files found.")  # noqa: T201
                return
        else:
            print(f"Found {len(migration_files)} migration files")  # noqa: T201

        files_to_clean = []

        for file_path in migration_files:
            uses_decorator, should_clean, reason = self.analyze_file(file_path)

            if uses_decorator and should_clean:
                files_to_clean.append(file_path)
                print(f"✓ {file_path.name} - {reason}")  # noqa: T201
            elif uses_decorator and not latest_only:
                print(f"⚠ {file_path.name} - {reason}")  # noqa: T201
            elif not latest_only:
                print(f"- {file_path.name} - {reason}")  # noqa: T201

        if not files_to_clean:
            if latest_only:
                print("Latest migration file does not need cleaning.")  # noqa: T201
            else:
                print("\nNo files need cleaning.")  # noqa: T201
            return

        if not latest_only:
            print(f"\nFiles that will be cleaned: {len(files_to_clean)}")  # noqa: T201
            for file_path in files_to_clean:
                print(f"  - {file_path.name}")  # noqa: T201

        if dry_run:
            print("\nDry run mode - no files were modified.")  # noqa: T201
            return

        # Skip confirmation if processing latest only
        if not latest_only:
            response = input(
                f"\nProceed with cleaning {len(files_to_clean)} files? (y/N): "
            )
            if response.lower() != "y":
                print("Cancelled.")  # noqa: T201
                return

        # Clean the files
        cleaned_count = 0
        for file_path in files_to_clean:
            if self.clean_file(file_path):
                cleaned_count += 1
                print(f"✓ Cleaned {file_path.name}")  # noqa: T201
            else:
                print(f"⚠ No changes made to {file_path.name}")  # noqa: T201

        if latest_only:
            if cleaned_count > 0:
                print("Latest migration file cleaned successfully.")  # noqa: T201
        else:
            print(f"\nCleaning complete. {cleaned_count} files were modified.")  # noqa: T201


def main():
    parser = argparse.ArgumentParser(
        description="Clean Alembic migration files by removing unnecessary "
        "for_each_project decorators"
    )
    parser.add_argument(
        "--migrations-dir",
        default="_alembic_migrations",
        help="Path to the Alembic migrations directory (default: _alembic_migrations)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without making changes",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Only process the newest migration file and skip confirmation",
    )

    args = parser.parse_args()

    try:
        cleaner = MigrationCleaner(args.migrations_dir)
        cleaner.run(dry_run=args.dry_run, latest_only=args.latest)
    except Exception as e:
        print(f"Error: {e}")  # noqa: T201
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
