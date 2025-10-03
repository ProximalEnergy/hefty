"""
Standalone enum validation script.

This script validates all BaseIntEnum subclasses against their database tables
without import conflicts that can occur when running the enumerations module directly.
"""

import sys
from pathlib import Path

# Add the src directory to the path to allow imports
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from core.dependencies import get_db_session
from core.enumerations import BaseIntEnum


def main() -> None:
    """Run enum validation against the database."""
    # Get database session without schema override (uses default schema mapping)
    session = get_db_session(schema=None)

    try:
        # Run validation with case-insensitive comparison since enum names are UPPER_CASE
        # and database names are typically lower_case
        results = BaseIntEnum.validate_all_enums(session=session)

        print("\n=== Enum Validation Results ===\n")  # noqa: T201

        for enum_name, result in results.items():
            print(f"{enum_name}:")  # noqa: T201
            print(f"  Valid: {result['valid']}")  # noqa: T201
            print(f"  Enum count: {result['total_enum_count']}")  # noqa: T201
            print(f"  DB count: {result['total_db_count']}")  # noqa: T201

            if result["missing_in_db"]:
                print(f"  Missing in DB: {result['missing_in_db']}")  # noqa: T201

            if result["extra_in_db"]:
                print(f"  Extra in DB: {result['extra_in_db']}")  # noqa: T201

            if result["name_mismatches"]:
                print(f"  Name mismatches: {result['name_mismatches']}")  # noqa: T201

            print()  # noqa: T201

        # Summary
        total_enums = len(results)
        valid_enums = sum(1 for r in results.values() if r["valid"])
        print(f"Summary: {valid_enums}/{total_enums} enums are valid")  # noqa: T201

        if valid_enums != total_enums:
            print("\nEnum validation failed.")  # noqa: T201
            sys.exit(1)

    finally:
        session.close()


if __name__ == "__main__":
    main()
