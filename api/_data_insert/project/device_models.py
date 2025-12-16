"""
Interactive script to update device_model_id in project.devices table.

This script allows you to:
- Select a project
- View device types and available device models
- Map device_type_id to device_model_id
- Update all devices with matching device_type_id
- Change projects during the session
"""

import json
import readline
import sys
import traceback
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from .. import utils


def get_projects(conn: Any) -> list[dict[str, Any]]:
    """Get all projects from operational.projects.

    Args:
        conn: TODO: describe.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT project_id, name_short, name_long
            FROM operational.projects
            ORDER BY name_short
            """,
        )
        return cursor.fetchall()


def get_device_types_in_project(
    conn: Any, project_name_short: str
) -> list[dict[str, Any]]:
    """Get unique device types used in a project.

    Args:
        conn: TODO: describe.
        project_name_short: TODO: describe.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            f"""
            SELECT DISTINCT dt.device_type_id, dt.name_short, dt.name_long
            FROM {project_name_short}.devices d
            JOIN operational.device_types dt
                ON d.device_type_id = dt.device_type_id
            ORDER BY dt.device_type_id
            """,
        )
        return cursor.fetchall()


def get_device_type_info(conn: Any, device_type_id: int) -> dict[str, Any] | None:
    """Get device type information by ID.

    Args:
        conn: TODO: describe.
        device_type_id: TODO: describe.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT device_type_id, name_short, name_long
            FROM operational.device_types
            WHERE device_type_id = %s
            """,
            (device_type_id,),
        )
        result = cursor.fetchone()
        return dict(result) if result else None


def get_device_model_info(
    conn: Any, device_model_id: int | None
) -> dict[str, Any] | None:
    """Get device model information by ID.

    Args:
        conn: TODO: describe.
        device_model_id: TODO: describe.
    """
    if device_model_id is None:
        return None
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT device_model_id, brand, model
            FROM operational.device_models
            WHERE device_model_id = %s
            """,
            (device_model_id,),
        )
        result = cursor.fetchone()
        return dict(result) if result else None


def get_device_models_for_type(conn: Any, device_type_id: int) -> list[dict[str, Any]]:
    """Get all device models for a specific device type.

    Args:
        conn: TODO: describe.
        device_type_id: TODO: describe.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT device_model_id, brand, model
            FROM operational.device_models
            WHERE device_type_id = %s
            ORDER BY device_model_id
            """,
            (device_type_id,),
        )
        return cursor.fetchall()


def get_device_count_by_type(
    conn: Any, project_name_short: str, device_type_id: int
) -> int:
    """Get count of devices with a specific device_type_id.

    Args:
        conn: TODO: describe.
        project_name_short: TODO: describe.
        device_type_id: TODO: describe.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {project_name_short}.devices
            WHERE device_type_id = %s
            """,
            (device_type_id,),
        )
        return cursor.fetchone()[0]


def get_current_device_model_id(
    conn: Any, project_name_short: str, device_type_id: int
) -> dict[int | None, int]:
    """Get count of devices by current device_model_id.

    Args:
        conn: TODO: describe.
        project_name_short: TODO: describe.
        device_type_id: TODO: describe.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            f"""
            SELECT device_model_id, COUNT(*) as count
            FROM {project_name_short}.devices
            WHERE device_type_id = %s
            GROUP BY device_model_id
            ORDER BY device_model_id NULLS LAST
            """,
            (device_type_id,),
        )
        return {row["device_model_id"]: row["count"] for row in cursor.fetchall()}


def update_device_models(
    conn: Any,
    project_name_short: str,
    device_type_id: int,
    device_model_id: int | None,
) -> int:
    """Update device_model_id for all devices with matching device_type_id.

    Args:
        conn: TODO: describe.
        project_name_short: TODO: describe.
        device_type_id: TODO: describe.
        device_model_id: TODO: describe.
    """
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            UPDATE {project_name_short}.devices
            SET device_model_id = %s
            WHERE device_type_id = %s
            """,
            (device_model_id, device_type_id),
        )
        updated_count = cursor.rowcount
        conn.commit()
        return updated_count


def get_device_model_distribution(
    conn: Any, project_name_short: str
) -> dict[int, dict[int | None, int]]:
    """Get device model distribution by device type for a project.

    Args:
        conn: TODO: describe.
        project_name_short: TODO: describe.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # First check if device_model_id column exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'devices'
            AND column_name = 'device_model_id'
            """,
            (project_name_short,),
        )
        if not cursor.fetchone():
            # Column doesn't exist, return empty dict
            return {}

        # Get distribution of device_model_id by device_type_id
        cursor.execute(
            f"""
            SELECT
                device_type_id,
                device_model_id,
                COUNT(*) as device_count
            FROM {project_name_short}.devices
            GROUP BY device_type_id, device_model_id
            ORDER BY device_type_id, device_model_id NULLS LAST
            """,
        )
        results = cursor.fetchall()

        # Build nested dictionary structure
        distribution: dict[int, dict[int | None, int]] = {}
        for row in results:
            device_type_id = row["device_type_id"]
            device_model_id = row["device_model_id"]
            device_count = row["device_count"]

            if device_type_id not in distribution:
                distribution[device_type_id] = {}

            distribution[device_type_id][device_model_id] = device_count

        return distribution


def update_project_spec_device_models(conn: Any, project_name_short: str) -> bool:
    """Update project spec with device_model_ids_by_device_type_id.

    Args:
        conn: TODO: describe.
        project_name_short: TODO: describe.
    """
    with conn.cursor() as cursor:
        # Get current spec - preserve all existing data
        cursor.execute(
            """
            SELECT spec
            FROM operational.projects
            WHERE name_short = %s
            """,
            (project_name_short,),
        )
        result = cursor.fetchone()
        if result is None:
            print(f"❌ Project '{project_name_short}' not found.")
            return False

        # Preserve existing spec data - if None, start with empty dict
        # but make a copy to avoid mutating the original
        existing_spec = result[0]
        if existing_spec is None:
            project_spec = {}
        else:
            # Make a deep copy to preserve all existing data
            project_spec = json.loads(json.dumps(existing_spec))

        # Get device model distribution
        distribution = get_device_model_distribution(conn, project_name_short)

        # Convert to the required format (strings for keys)
        # Only include device_type_ids that have at least one non-null device_model_id
        device_model_ids_by_device_type_id: dict[str, dict[str, int]] = {}
        for device_type_id, model_counts in distribution.items():
            # Filter out None/null device_model_ids
            non_null_counts = {
                str(model_id): count
                for model_id, count in model_counts.items()
                if model_id is not None
            }
            # Only add this device_type_id if it has at least one non-null model
            if non_null_counts:
                device_model_ids_by_device_type_id[str(device_type_id)] = (
                    non_null_counts
                )

        # Update only the specific field, preserving all other spec data
        project_spec["device_model_ids_by_device_type_id"] = (
            device_model_ids_by_device_type_id
        )

        # Update in database using jsonb_set to preserve existing data
        cursor.execute(
            """
            UPDATE operational.projects
            SET spec = spec || %s::jsonb
            WHERE name_short = %s
            """,
            (
                json.dumps(
                    {
                        "device_model_ids_by_device_type_id": device_model_ids_by_device_type_id
                    }
                ),
                project_name_short,
            ),
        )

        conn.commit()
        return True


def display_projects(projects: list[dict[str, Any]]) -> None:
    """Display list of projects.

    Args:
        projects: TODO: describe.
    """
    print("\n" + "=" * 60)
    print("Available Projects:")
    print("=" * 60)
    for project in projects:
        print(
            f"{project['name_short']}. {project['name_long']} "
            f"(ID: {project['project_id']})"
        )


def display_device_types(device_types: list[dict[str, Any]]) -> None:
    """Display list of device types.

    Args:
        device_types: TODO: describe.
    """
    print("\n" + "=" * 60)
    print("Device Types in Project:")
    print("=" * 60)
    for dt in device_types:
        print(f"{dt['device_type_id']}. {dt['name_short']} - {dt['name_long']}")


def display_device_models(device_models: list[dict[str, Any]]) -> None:
    """Display list of device models.

    Args:
        device_models: TODO: describe.
    """
    print("\n" + "=" * 60)
    print("Available Device Models:")
    print("=" * 60)
    print("0. None (clear device_model_id)")
    for dm in device_models:
        print(f"{dm['device_model_id']}. {dm['brand']} {dm['model']}")


class ProjectCompleter:
    """Tab completer for project names."""

    def __init__(self, projects: list[dict[str, Any]]):
        """todo

        Args:
            self: TODO: describe.
            projects: TODO: describe.
        """
        self.projects = projects
        self.matches: list[str] = []

    def complete(self, text: str, state: int) -> str | None:
        """Complete project name based on text input.

        Args:
            self: TODO: describe.
            text: TODO: describe.
            state: TODO: describe.
        """
        if state == 0:
            # First call: build list of matches
            text_lower = text.lower()
            self.matches = []
            name_matches = []
            uuid_matches = []

            for project in self.projects:
                name_short = project["name_short"]
                project_id = str(project["project_id"])
                # Match by name_short (preferred)
                if name_short.lower().startswith(text_lower):
                    name_matches.append(name_short)
                # Match by UUID prefix (fallback)
                elif project_id.lower().startswith(text_lower):
                    uuid_matches.append(project_id)

            # Sort and combine: name matches first, then UUID matches
            self.matches = sorted(name_matches) + sorted(uuid_matches)

        # Return the next match
        try:
            return self.matches[state]
        except IndexError:
            return None


def select_project(
    projects: list[dict[str, Any]], current_project: dict[str, Any] | None = None
) -> dict[str, Any] | str | None:
    """Interactive project selection with tab completion.

        Returns:
            dict: Selected project
            "__DEACTIVATE__": User wants to deactivate current project
            None: User cancelled/back

    Args:
        projects: TODO: describe.
        current_project: TODO: describe.
    """
    display_projects(projects)
    if current_project:
        print("\nd. Deactivate current project")
    print("\n0. Back")
    print("💡 Tip: Press TAB to autocomplete project names!")

    # Set up tab completion
    completer = ProjectCompleter(projects)
    old_completer = readline.get_completer()
    readline.set_completer(completer.complete)
    # Enable tab completion
    readline.parse_and_bind("tab: complete")
    # Configure readline for better UX
    # Allow completion to show all matches if ambiguous
    readline_doc = readline.__doc__ or ""
    if "libedit" in readline_doc:
        # macOS uses libedit
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        # GNU readline
        readline.parse_and_bind("set show-all-if-ambiguous on")
        readline.parse_and_bind("set completion-ignore-case on")

    try:
        choice = input("\nSelect project (name_short or ID): ").strip().lower()
        if choice == "0":
            return None
        if choice == "d" and current_project:
            return "__DEACTIVATE__"
        # Try to match by name_short first (most common case)
        for project in projects:
            if project["name_short"].lower() == choice:
                return project
        # If not found by name, try to match by project_id (UUID)
        for project in projects:
            if str(project["project_id"]).lower() == choice:
                return project
        print("❌ Invalid selection.")
        return None
    except (ValueError, KeyboardInterrupt):
        return None
    finally:
        # Restore previous completer
        if old_completer is not None:
            readline.set_completer(old_completer)
        else:
            readline.set_completer(None)


def select_device_type(
    device_types: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Interactive device type selection.

    Args:
        device_types: TODO: describe.
    """
    display_device_types(device_types)
    print("\n0. Back")
    try:
        choice = input("\nSelect device type (ID): ").strip()
        if choice == "0":
            return None
        device_type_id = int(choice)
        for dt in device_types:
            if dt["device_type_id"] == device_type_id:
                return dt
        print("❌ Invalid selection.")
        return None
    except (ValueError, KeyboardInterrupt):
        return None


def select_device_model(
    device_models: list[dict[str, Any]],
) -> int | None:
    """Interactive device model selection.

    Args:
        device_models: TODO: describe.
    """
    display_device_models(device_models)
    print("\nb. Back")
    try:
        choice = (
            input("\nSelect device model (ID, 0 for None, or 'b' to go back): ")
            .strip()
            .lower()
        )
        if choice == "b" or choice == "":
            return None
        if choice == "0":
            return None  # User selected "None" to clear device_model_id
        device_model_id = int(choice)
        for dm in device_models:
            if dm["device_model_id"] == device_model_id:
                return device_model_id
        print("❌ Invalid selection.")
        return None
    except (ValueError, KeyboardInterrupt):
        return None


def get_existing_mappings(conn: Any, project_name_short: str) -> list[dict[str, Any]]:
    """Get existing device_type_id -> device_model_id mappings in a project.

    Args:
        conn: TODO: describe.
        project_name_short: TODO: describe.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        # First check if device_model_id column exists
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'devices'
            AND column_name = 'device_model_id'
            """,
            (project_name_short,),
        )
        if not cursor.fetchone():
            # Column doesn't exist, return empty list
            return []

        # Column exists, proceed with the query using explicit schema qualification
        cursor.execute(
            f"""
            SELECT
                d.device_type_id,
                dt.name_short as device_type_name_short,
                dt.name_long as device_type_name_long,
                d.device_model_id,
                dm.brand,
                dm.model,
                COUNT(*) as device_count
            FROM {project_name_short}.devices d
            JOIN operational.device_types dt
                ON d.device_type_id = dt.device_type_id
            LEFT JOIN operational.device_models dm
                ON d.device_model_id = dm.device_model_id
            GROUP BY
                d.device_type_id,
                dt.name_short,
                dt.name_long,
                d.device_model_id,
                dm.brand,
                dm.model
            ORDER BY d.device_type_id, d.device_model_id NULLS LAST
            """,
        )
        return cursor.fetchall()


def display_existing_mappings(mappings: list[dict[str, Any]]) -> None:
    """Display existing device_type_id -> device_model_id mappings.

    Args:
        mappings: TODO: describe.
    """
    print("\n" + "=" * 60)
    print("Existing Device Model Mappings:")
    print("=" * 60)
    if not mappings:
        print("No mappings found.")
        return

    for mapping in mappings:
        device_type_id = mapping["device_type_id"]
        device_type_name = mapping["device_type_name_short"]
        device_model_id = mapping["device_model_id"]
        device_count = mapping["device_count"]

        if device_model_id is None:
            model_info = "None (not set)"
        else:
            brand = mapping["brand"] or "N/A"
            model = mapping["model"] or "N/A"
            model_info = f"{brand} {model} (ID: {device_model_id})"

        print(
            f"Device Type: {device_type_id} ({device_type_name}) -> "
            f"{model_info} - {device_count} device(s)"
        )


def preview_update(
    conn: Any,
    project_name_short: str,
    device_type_id: int,
    device_model_id: int | None,
) -> None:
    """Show preview of what will be updated.

    Args:
        conn: TODO: describe.
        project_name_short: TODO: describe.
        device_type_id: TODO: describe.
        device_model_id: TODO: describe.
    """
    total_count = get_device_count_by_type(conn, project_name_short, device_type_id)
    current_distribution = get_current_device_model_id(
        conn, project_name_short, device_type_id
    )

    # Get device type and model info for display
    dt_info = get_device_type_info(conn, device_type_id)
    dm_info = get_device_model_info(conn, device_model_id)

    device_type_str = (
        f"{dt_info['name_short']} ({device_type_id})"
        if dt_info
        else f"ID: {device_type_id}"
    )
    device_model_str = (
        f"{dm_info['brand']} {dm_info['model']} ({device_model_id})"
        if dm_info
        else "None"
        if device_model_id is None
        else f"ID: {device_model_id}"
    )

    print("\n" + "=" * 60)
    print("Update Preview:")
    print("=" * 60)
    print(f"Project: {project_name_short}")
    print(f"Device Type: {device_type_str}")
    print(f"New Device Model: {device_model_str}")
    print(f"\nTotal devices to update: {total_count}")
    print("\nCurrent distribution:")
    for model_id, count in current_distribution.items():
        if model_id is None:
            model_display = "None (not set)"
        else:
            current_dm_info = get_device_model_info(conn, model_id)
            if current_dm_info:
                model_display = (
                    f"{current_dm_info['brand']} {current_dm_info['model']} "
                    f"({model_id})"
                )
            else:
                model_display = f"ID: {model_id}"
        print(f"  {model_display}: {count} device(s)")
    model_name_for_summary = (
        f"{dm_info['brand']} {dm_info['model']}" if dm_info else "None"
    )
    print(
        f"\nAfter update: All {total_count} device(s) will have "
        f"device_model_id={device_model_id} ({model_name_for_summary})"
    )


def main() -> None:
    """Main interactive loop."""
    print("=" * 60)
    print("Device Model Update Script")
    print("=" * 60)

    try:
        with psycopg2.connect(
            utils.CONNECTION_STRING,
            application_name=utils.application_name(__file__),
        ) as conn:
            # Get all projects
            projects = get_projects(conn)
            if not projects:
                print("⚠️  No projects found in database.")
                return

            current_project: dict[str, Any] | None = None
            pending_updates: list[tuple[str, int, int | None]] = []

            while True:
                print("\n" + "=" * 60)
                print("Main Menu")
                print("=" * 60)
                if current_project:
                    print(f"Current Project: {current_project['name_short']}")
                else:
                    print("No project selected")

                # Show pending updates inline
                if pending_updates:
                    print("\n📋 Pending Updates:")
                    for idx, (proj, dt_id, dm_id) in enumerate(pending_updates, 1):
                        count = get_device_count_by_type(conn, proj, dt_id)
                        dt_info = get_device_type_info(conn, dt_id)
                        dm_info = get_device_model_info(conn, dm_id)

                        device_type_str = (
                            f"{dt_info['name_short']} ({dt_id})"
                            if dt_info
                            else f"ID: {dt_id}"
                        )
                        device_model_str = (
                            f"{dm_info['brand']} {dm_info['model']} ({dm_id})"
                            if dm_info
                            else "None"
                            if dm_id is None
                            else f"ID: {dm_id}"
                        )

                        print(
                            f"  {idx}. {proj}: {device_type_str} -> "
                            f"{device_model_str} ({count} devices)"
                        )
                else:
                    print("\n📋 No pending updates")

                print("\n1. Select/Change Project")
                print("2. View Existing Mappings")
                print("3. Add Update Mapping")
                print("4. Apply All Updates")
                print("5. Clear Pending Updates")
                print("6. Update Project Spec (device_model_ids_by_device_type_id)")
                print("0. Exit")

                try:
                    choice = input("\nSelect option: ").strip()

                    if choice == "0":
                        if pending_updates:
                            confirm = (
                                input(
                                    "\nYou have pending updates. Exit anyway? (y/N): "
                                )
                                .strip()
                                .lower()
                            )
                            if confirm != "y":
                                continue
                        print("\nExiting...")
                        break

                    elif choice == "1":
                        # Select/Change Project
                        selected = select_project(projects, current_project)
                        if selected == "__DEACTIVATE__":
                            current_project = None
                            print("\n✅ Project deactivated.")
                        elif selected:
                            current_project = selected
                            print(
                                f"\n✅ Project selected: {current_project['name_short']}"
                            )

                    elif choice == "2":
                        # View Existing Mappings
                        if not current_project:
                            print("\n⚠️  Please select a project first.")
                            continue

                        project_name_short = current_project["name_short"]
                        mappings = get_existing_mappings(conn, project_name_short)
                        display_existing_mappings(mappings)
                        input("\nPress Enter to continue...")

                    elif choice == "3":
                        # Add Update Mapping
                        if not current_project:
                            print("\n⚠️  Please select a project first.")
                            continue

                        project_name_short = current_project["name_short"]
                        device_types = get_device_types_in_project(
                            conn, project_name_short
                        )

                        if not device_types:
                            print("\n⚠️  No device types found in this project.")
                            continue

                        selected_dt = select_device_type(device_types)
                        if not selected_dt:
                            continue

                        device_type_id = selected_dt["device_type_id"]
                        device_models = get_device_models_for_type(conn, device_type_id)

                        if not device_models:
                            print(
                                f"\n⚠️  No device models found for device type "
                                f"{selected_dt['name_short']}."
                            )
                            continue

                        selected_model_id = select_device_model(device_models)
                        if selected_model_id is None:
                            continue

                        # Show preview
                        preview_update(
                            conn,
                            project_name_short,
                            device_type_id,
                            selected_model_id,
                        )

                        confirm = (
                            input("\nAdd this update to pending list? (y/N): ")
                            .strip()
                            .lower()
                        )
                        if confirm == "y":
                            pending_updates.append(
                                (project_name_short, device_type_id, selected_model_id)
                            )
                            print("\n✅ Update added to pending list!")

                    elif choice == "4":
                        # Apply All Updates
                        if not pending_updates:
                            print("\nℹ️  No pending updates to apply.")
                            continue

                        print("\n" + "=" * 60)
                        print("Apply Updates")
                        print("=" * 60)
                        for idx, (proj, dt_id, dm_id) in enumerate(pending_updates, 1):
                            count = get_device_count_by_type(conn, proj, dt_id)
                            dt_info = get_device_type_info(conn, dt_id)
                            dm_info = get_device_model_info(conn, dm_id)

                            device_type_str = (
                                f"{dt_info['name_short']} ({dt_id})"
                                if dt_info
                                else f"ID: {dt_id}"
                            )
                            device_model_str = (
                                f"{dm_info['brand']} {dm_info['model']} ({dm_id})"
                                if dm_info
                                else "None"
                                if dm_id is None
                                else f"ID: {dm_id}"
                            )

                            print(
                                f"{idx}. Project: {proj}\n"
                                f"   Device Type: {device_type_str}\n"
                                f"   Device Model: {device_model_str}\n"
                                f"   Devices: {count}"
                            )

                        print("\n" + "=" * 60)
                        print("⚠️  WARNING: This will UPDATE the DATABASE!")
                        print("=" * 60)
                        print(
                            "This operation will permanently modify device_model_id "
                            "values in the database for all devices matching the "
                            "specified device types."
                        )
                        confirm = (
                            input(
                                "\n⚠️  Are you sure you want to apply all updates? (y/N): "
                            )
                            .strip()
                            .lower()
                        )
                        if confirm != "y":
                            continue

                        print("\n🔄 Applying updates...")
                        for proj, dt_id, dm_id in pending_updates:
                            updated = update_device_models(conn, proj, dt_id, dm_id)
                            dt_info = get_device_type_info(conn, dt_id)
                            dm_info = get_device_model_info(conn, dm_id)

                            device_type_str = (
                                f"{dt_info['name_short']} ({dt_id})"
                                if dt_info
                                else f"ID: {dt_id}"
                            )
                            device_model_str = (
                                f"{dm_info['brand']} {dm_info['model']} ({dm_id})"
                                if dm_info
                                else "None"
                                if dm_id is None
                                else f"ID: {dm_id}"
                            )

                            print(
                                f"✅ Updated {updated} devices in {proj}\n"
                                f"   Device Type: {device_type_str}\n"
                                f"   Device Model: {device_model_str}"
                            )

                        pending_updates = []
                        print("\n🎉 All updates applied successfully!")

                    elif choice == "5":
                        # Clear Pending Updates
                        if not pending_updates:
                            print("\nℹ️  No pending updates to clear.")
                        else:
                            confirm = (
                                input("\nClear all pending updates? (y/N): ")
                                .strip()
                                .lower()
                            )
                            if confirm == "y":
                                pending_updates = []
                                print("\n✅ Pending updates cleared.")

                    elif choice == "6":
                        # Update Project Spec
                        print("\n" + "=" * 60)
                        print("⚠️  WARNING: This will UPDATE the DATABASE!")
                        print("=" * 60)
                        print(
                            "This operation will update the 'device_model_ids_by_device_type_id' "
                            "field in operational.projects.spec for one or more projects."
                        )

                        if current_project:
                            project_name_short = current_project["name_short"]
                            print(f"\nSelected project: {project_name_short}")
                            projects_to_update = [current_project]
                        else:
                            print("\nNo project selected - will update ALL projects.")
                            projects_to_update = projects

                        confirm = (
                            input(
                                f"\n⚠️  Update spec for {len(projects_to_update)} project(s)? (y/N): "
                            )
                            .strip()
                            .lower()
                        )
                        if confirm != "y":
                            continue

                        print("\n🔄 Updating project spec(s)...")
                        success_count = 0
                        failed_count = 0

                        for project in projects_to_update:
                            project_name_short = project["name_short"]
                            print(f"\n  Processing {project_name_short}...", end=" ")

                            success = update_project_spec_device_models(
                                conn, project_name_short
                            )
                            if success:
                                print("✅")
                                success_count += 1
                            else:
                                print("❌")
                                failed_count += 1

                        print("\n" + "=" * 60)
                        print("Update Summary:")
                        print("=" * 60)
                        print(f"✅ Successfully updated: {success_count} project(s)")
                        if failed_count > 0:
                            print(f"❌ Failed: {failed_count} project(s)")
                        print(
                            "\nAdded/updated 'device_model_ids_by_device_type_id' "
                            "in operational.projects.spec"
                        )

                    else:
                        print("\n❌ Invalid option. Please try again.")

                except KeyboardInterrupt:
                    print("\n\nInterrupted. Exiting...")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    traceback.print_exc()

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
