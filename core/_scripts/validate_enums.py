"""
Standalone enum validation script.

This script validates all BaseIntEnum subclasses against their database tables
without import conflicts that can occur when running the enumerations module directly.
It can also automatically update the enumerations.py file with missing entries.
"""

import re
import sys
from pathlib import Path

# Add the src directory to the path to allow imports
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from core.database import get_db_session  # noqa: E402
from core.enumerations import BaseIntEnum  # noqa: E402


def db_name_to_enum_name(db_name: str) -> str:
    """Convert database name to valid Python enum name (UPPER_CASE).

    Args:
        db_name: Database name (typically lower_case or mixed case).

    Returns:
        Valid Python identifier in UPPER_CASE format.
    """
    # Replace non-alphanumeric characters with underscores
    name = re.sub(r"[^a-zA-Z0-9_]", "_", db_name)
    # Replace multiple underscores with single underscore
    name = re.sub(r"_+", "_", name)
    # Remove leading/trailing underscores
    name = name.strip("_")
    # Convert to uppercase
    name = name.upper()
    # Ensure it starts with a letter or underscore
    if name and not name[0].isalpha() and name[0] != "_":
        name = f"_{name}"
    # If empty, use a default
    if not name:
        name = "UNKNOWN"
    return name


def update_enumerations_file(
    enum_file_path: Path,
    updates: dict[str, list[dict[str, int | str]]],
) -> bool:
    """Update enumerations.py file with new enum members.

    Args:
        enum_file_path: Path to the enumerations.py file.
        updates: Dictionary mapping enum class names to lists of new members.
                 Each member dict has 'id' and 'db_name' keys.

    Returns:
        True if file was updated, False otherwise.
    """
    if not updates:
        return False

    content = enum_file_path.read_text()
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Check if this is a class definition for an enum we need to update
        class_match = re.match(r"^class (\w+)\(BaseIntEnum\):", line)
        if class_match:
            enum_class_name = class_match.group(1)
            if enum_class_name in updates:
                # Skip the class definition line
                i += 1

                # Collect metadata lines (nonmember assignments and blank lines)
                while i < len(lines):
                    stripped = lines[i].strip()
                    if stripped.startswith(("_db_", "#")) or stripped == "":
                        new_lines.append(lines[i])
                        i += 1
                    else:
                        break

                # Collect existing enum members with their original lines
                existing_members: dict[
                    int, tuple[str, str]
                ] = {}  # value -> (name, original_line)
                while i < len(lines):
                    stripped = lines[i].strip()
                    # Stop if we hit another class definition
                    if stripped.startswith("class "):
                        break
                    # Check if it's an enum member (NAME = VALUE)
                    member_match = re.match(r"^(\w+)\s*=\s*(\d+)\s*(.*)$", stripped)
                    if member_match:
                        name = member_match.group(1)
                        value = int(member_match.group(2))
                        existing_members[value] = (name, lines[i])
                        i += 1
                    elif not stripped:
                        # Blank line - stop collecting enum members
                        # (blank line will be processed in next iteration)
                        break
                    else:
                        # Not an enum member, might be a comment or other line
                        # Keep it as-is but continue looking for enum members
                        new_lines.append(lines[i])
                        i += 1

                # Create new members from updates
                new_members: list[tuple[int, str, str]] = []  # (value, name, db_name)
                for extra in updates[enum_class_name]:
                    db_name = str(extra["db_name"])
                    enum_id = int(extra["id"])
                    enum_name = db_name_to_enum_name(db_name)
                    if enum_id not in existing_members:
                        new_members.append((enum_id, enum_name, db_name))

                # Merge existing and new members, sort by value
                all_members: list[
                    tuple[int, str, str | None, bool]
                ] = []  # (value, name, original_line, is_new)
                for value, (name, orig_line) in existing_members.items():
                    all_members.append((value, name, orig_line, False))
                for value, name, db_name in new_members:
                    all_members.append((value, name, None, True))

                # Sort by value
                all_members.sort(key=lambda x: x[0])

                # Write enum members
                for value, name, orig_line, is_new in all_members:
                    if is_new:
                        # Find the db_name for this member
                        db_name = next(
                            (
                                str(extra["db_name"])
                                for extra in updates[enum_class_name]
                                if int(extra["id"]) == value
                            ),
                            "",
                        )
                        new_lines.append(f"    {name} = {value}")
                    else:
                        # Preserve original line
                        new_lines.append(orig_line)

                # Continue processing (don't increment i here as we already did)
                continue

        i += 1

    # Write updated content
    new_content = "\n".join(new_lines)
    if new_content != content:
        enum_file_path.write_text(new_content)
        return True
    return False


def main() -> None:
    """Run enum validation against the database and update enumerations.py if needed."""
    # Get database session without schema override (uses default schema mapping)
    session = get_db_session(schema=None)

    try:
        # Run validation with case-insensitive comparison since enum names are
        # UPPER_CASE and database names are typically lower_case
        results = BaseIntEnum.validate_all_enums(session=session)

        print("\n=== Enum Validation Results ===\n")  # noqa: T201

        # Collect updates for enums with extra_in_db entries
        updates: dict[str, list[dict[str, int | str]]] = {}

        for enum_name, result in results.items():
            print(f"{enum_name}:")  # noqa: T201
            print(f"  Valid: {result['valid']}")  # noqa: T201
            print(f"  Enum count: {result['total_enum_count']}")  # noqa: T201
            print(f"  DB count: {result['total_db_count']}")  # noqa: T201

            if result["missing_in_db"]:
                print(f"  Missing in DB: {result['missing_in_db']}")  # noqa: T201

            if result["extra_in_db"]:
                print("  Extra in DB:")  # noqa: T201
                for extra in result["extra_in_db"]:
                    enum_name_upper = db_name_to_enum_name(str(extra["db_name"]))
                    print(  # noqa: T201
                        f"    {enum_name_upper} = {extra['id']} "
                        f"(from DB: {extra['db_name']})"
                    )
                # Collect for update
                updates[enum_name] = result["extra_in_db"]

            if result["name_mismatches"]:
                print(f"  Name mismatches: {result['name_mismatches']}")  # noqa: T201

            print()  # noqa: T201

        # Summary
        total_enums = len(results)
        valid_enums = sum(1 for r in results.values() if r["valid"])
        print(f"Summary: {valid_enums}/{total_enums} enums are valid")  # noqa: T201

        # Update enumerations.py if there are updates
        if updates:
            enum_file_path = (
                Path(__file__).parent.parent / "src" / "core" / "enumerations.py"
            )
            print("\n=== Updating enumerations.py ===\n")  # noqa: T201
            updated = update_enumerations_file(enum_file_path, updates)
            if updated:
                print("Successfully updated enumerations.py with new enum members:\n")  # noqa: T201
                for enum_name, extra_list in updates.items():
                    print(f"  {enum_name}:")  # noqa: T201
                    for extra in extra_list:
                        enum_name_upper = db_name_to_enum_name(str(extra["db_name"]))
                        print(  # noqa: T201
                            f"    + {enum_name_upper} = {extra['id']} "
                            f"(from DB: {extra['db_name']})"
                        )
                    print()  # noqa: T201
            else:
                print("No changes needed in enumerations.py.")  # noqa: T201

        if valid_enums != total_enums and not updates:
            print("\nEnum validation failed.")  # noqa: T201
            sys.exit(1)

    finally:
        session.close()


if __name__ == "__main__":
    main()
