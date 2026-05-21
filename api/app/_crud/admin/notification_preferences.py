from typing import Any, Literal, cast
from uuid import UUID

import sqlalchemy as sa
from core.db_query import DbQuery, OutputType
from sqlalchemy import Table, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models

_NOTIFICATION_SEVERITY_COLUMNS = (
    "in_app_min_severity",
    "email_min_severity",
)


def _normalize_notification_severity(*, value: Any) -> Any:
    if isinstance(value, enumerations.NotificationSeverity):
        return value.value

    if not isinstance(value, str):
        return value

    try:
        return enumerations.NotificationSeverity(value).value
    except ValueError:
        pass

    try:
        return enumerations.NotificationSeverity[value].value
    except KeyError:
        return value


def normalize_notification_preference_records(
    *,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize preference enum values for API response models.

    Args:
        records: List of preference record dictionaries.
    """
    for record in records:
        for column in _NOTIFICATION_SEVERITY_COLUMNS:
            if column in record:
                record[column] = _normalize_notification_severity(
                    value=record[column],
                )
    return records


def apply_notification_preference_updates(
    *,
    preference: models.NotificationPreference,
    in_app_enabled: bool | None = None,
    email_enabled: bool | None = None,
    in_app_min_severity: enumerations.NotificationSeverity | None = None,
    email_min_severity: enumerations.NotificationSeverity | None = None,
) -> None:
    """Apply notification preference field updates in memory.

    Args:
        preference: ORM preference object to mutate.
        in_app_enabled: Override in-app enabled flag, if provided.
        email_enabled: Override email enabled flag, if provided.
        in_app_min_severity: Override in-app minimum severity, if provided.
        email_min_severity: Override email minimum severity, if provided.
    """
    if in_app_enabled is not None:
        preference.in_app_enabled = in_app_enabled
    if email_enabled is not None:
        preference.email_enabled = email_enabled
    if in_app_min_severity is not None:
        preference.in_app_min_severity = in_app_min_severity
    if email_min_severity is not None:
        preference.email_min_severity = email_min_severity


def get_user_notification_preference(
    *,
    user_id: str,
    project_id: UUID,
    notification_type_id: int,
) -> DbQuery[models.NotificationPreference, Literal[True]]:
    """Get a specific notification preference.

    Args:
        user_id: User ID.
        project_id: Project ID.
        notification_type_id: Notification type ID.
    """
    query = select(models.NotificationPreference).where(
        models.NotificationPreference.user_id == user_id,
        models.NotificationPreference.project_id == project_id,
        models.NotificationPreference.notification_type_id == notification_type_id,
    )
    return DbQuery(query=query, is_scalar=True)


def get_user_notification_preferences_query(
    *,
    user_id: str,
    project_ids: list[UUID] | None = None,
) -> DbQuery[models.NotificationPreference, Literal[False]]:
    """Build query for notification preferences for a user.

    Args:
        user_id: User ID.
        project_ids: Optional project IDs to filter by.
    """
    query = select(models.NotificationPreference).where(
        models.NotificationPreference.user_id == user_id
    )
    if project_ids:
        query = query.where(models.NotificationPreference.project_id.in_(project_ids))
    return DbQuery(query=query)


def get_notification_type_query(
    *,
    notification_type_id: int,
) -> DbQuery[models.NotificationType, Literal[True]]:
    """Build query for a single notification type.

    Args:
        notification_type_id: Notification type ID.
    """
    query = select(models.NotificationType).where(
        models.NotificationType.notification_type_id == notification_type_id
    )
    return DbQuery(query=query, is_scalar=True)


def get_notification_types_query(
    *,
    notification_type_ids: list[int],
) -> DbQuery[models.NotificationType, Literal[False]]:
    """Build query for many notification types.

    Args:
        notification_type_ids: Notification type IDs.
    """
    query = select(models.NotificationType).where(
        models.NotificationType.notification_type_id.in_(notification_type_ids)
    )
    return DbQuery(query=query)


def get_bulk_user_notification_preferences_query(
    *,
    user_id: str,
    project_ids: list[UUID],
    notification_type_ids: list[int],
) -> DbQuery[models.NotificationPreference, Literal[False]]:
    """Build query for many user notification preferences.

    Args:
        user_id: User ID.
        project_ids: Project IDs to filter by.
        notification_type_ids: Notification type IDs to filter by.
    """
    query = select(models.NotificationPreference).where(
        models.NotificationPreference.user_id == user_id,
        models.NotificationPreference.project_id.in_(project_ids),
        models.NotificationPreference.notification_type_id.in_(notification_type_ids),
    )
    return DbQuery(query=query)


def upsert_bulk_user_notification_preferences_query(
    *,
    user_id: str,
    project_ids: list[UUID],
    notification_type_ids: list[int],
    in_app_enabled: bool | None = None,
    email_enabled: bool | None = None,
    in_app_min_severity: enumerations.NotificationSeverity | None = None,
    email_min_severity: enumerations.NotificationSeverity | None = None,
) -> DbQuery[Any, Literal[False]]:
    """Build an upsert for many notification preferences.

    Args:
        user_id: ID of the user whose preferences are updated.
        project_ids: Project IDs to update preferences for.
        notification_type_ids: Notification type IDs to update.
        in_app_enabled: Override in-app enabled flag, if provided.
        email_enabled: Override email enabled flag, if provided.
        in_app_min_severity: Override in-app minimum severity, if provided.
        email_min_severity: Override email minimum severity, if provided.
    """
    preferences_table = cast(Table, models.NotificationPreference.__table__)
    requested_preferences = (
        sa.values(
            sa.column("project_id", preferences_table.c.project_id.type),
            sa.column(
                "notification_type_id",
                preferences_table.c.notification_type_id.type,
            ),
            name="requested_preferences",
        )
        .data(
            [
                (project_id, notification_type_id)
                for project_id in project_ids
                for notification_type_id in notification_type_ids
            ]
        )
        .alias()
    )

    default_severity = sa.literal(
        enumerations.NotificationSeverity.INFO,
        type_=models.notification_severity_enum,
    )
    insert_select = (
        select(
            sa.literal(user_id).label("user_id"),
            requested_preferences.c.project_id,
            requested_preferences.c.notification_type_id,
            (
                sa.literal(in_app_enabled)
                if in_app_enabled is not None
                else models.NotificationType.in_app_enabled_default
            ).label("in_app_enabled"),
            (
                sa.literal(email_enabled)
                if email_enabled is not None
                else models.NotificationType.email_enabled_default
            ).label("email_enabled"),
            (
                sa.literal(
                    in_app_min_severity,
                    type_=models.notification_severity_enum,
                )
                if in_app_min_severity is not None
                else sa.func.coalesce(
                    models.NotificationType.in_app_severity_default,
                    default_severity,
                )
            ).label("in_app_min_severity"),
            (
                sa.literal(
                    email_min_severity,
                    type_=models.notification_severity_enum,
                )
                if email_min_severity is not None
                else sa.func.coalesce(
                    models.NotificationType.email_severity_default,
                    default_severity,
                )
            ).label("email_min_severity"),
        )
        .select_from(requested_preferences)
        .join(
            models.NotificationType,
            models.NotificationType.notification_type_id
            == requested_preferences.c.notification_type_id,
        )
    )

    insert_stmt = pg_insert(preferences_table).from_select(
        [
            preferences_table.c.user_id,
            preferences_table.c.project_id,
            preferences_table.c.notification_type_id,
            preferences_table.c.in_app_enabled,
            preferences_table.c.email_enabled,
            preferences_table.c.in_app_min_severity,
            preferences_table.c.email_min_severity,
        ],
        insert_select,
    )
    update_values: dict[str, Any] = {}
    if in_app_enabled is not None:
        update_values["in_app_enabled"] = insert_stmt.excluded.in_app_enabled
    if email_enabled is not None:
        update_values["email_enabled"] = insert_stmt.excluded.email_enabled
    if in_app_min_severity is not None:
        update_values["in_app_min_severity"] = insert_stmt.excluded.in_app_min_severity
    if email_min_severity is not None:
        update_values["email_min_severity"] = insert_stmt.excluded.email_min_severity

    conflict_columns = [
        preferences_table.c.user_id,
        preferences_table.c.project_id,
        preferences_table.c.notification_type_id,
    ]
    if update_values:
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=conflict_columns,
            set_=update_values,
        )
    else:
        upsert_stmt = insert_stmt.on_conflict_do_nothing(
            index_elements=conflict_columns,
        )
    returning_stmt = upsert_stmt.returning(*preferences_table.c)
    return DbQuery(query=returning_stmt)


async def get_or_create_notification_preference(
    *,
    db: AsyncSession,
    user_id: str,
    project_id: UUID,
    notification_type_id: int,
) -> models.NotificationPreference:
    """Get or create a notification preference with defaults from notification type.

    Args:
        db: Database session.
        user_id: User ID.
        project_id: Project ID.
        notification_type_id: Notification type ID.
    """
    # Try to get existing preference (use same session so object stays attached)
    preference = await get_user_notification_preference(
        user_id=user_id,
        project_id=project_id,
        notification_type_id=notification_type_id,
    ).get_async(executor=db, output_type=OutputType.SQLALCHEMY)

    if preference is not None:
        return preference

    # Get notification type for defaults
    notification_type = await get_notification_type_query(
        notification_type_id=notification_type_id,
    ).get_async(executor=db, output_type=OutputType.SQLALCHEMY)
    if notification_type is None:
        raise ValueError(f"Notification type {notification_type_id} does not exist")

    # Create new preference with defaults
    new_preference = models.NotificationPreference(
        user_id=user_id,
        project_id=project_id,
        notification_type_id=notification_type_id,
        in_app_enabled=notification_type.in_app_enabled_default,
        email_enabled=notification_type.email_enabled_default,
        in_app_min_severity=(
            notification_type.in_app_severity_default
            or enumerations.NotificationSeverity.INFO
        ),
        email_min_severity=(
            notification_type.email_severity_default
            or enumerations.NotificationSeverity.INFO
        ),
    )
    db.add(new_preference)
    await db.commit()
    await db.refresh(new_preference)
    return new_preference


async def update_notification_preference(
    *,
    db: AsyncSession,
    user_id: str,
    project_id: UUID,
    notification_type_id: int,
    in_app_enabled: bool | None = None,
    email_enabled: bool | None = None,
    in_app_min_severity: enumerations.NotificationSeverity | None = None,
    email_min_severity: enumerations.NotificationSeverity | None = None,
) -> models.NotificationPreference:
    """Update a notification preference.

    Args:
        db: Database session.
        user_id: User ID.
        project_id: Project ID.
        notification_type_id: Notification type ID.
        in_app_enabled: Optional in-app enabled flag.
        email_enabled: Optional email enabled flag.
        in_app_min_severity: Optional in-app minimum severity.
        email_min_severity: Optional email minimum severity.
    """
    preference = await get_or_create_notification_preference(
        db=db,
        user_id=user_id,
        project_id=project_id,
        notification_type_id=notification_type_id,
    )

    apply_notification_preference_updates(
        preference=preference,
        in_app_enabled=in_app_enabled,
        email_enabled=email_enabled,
        in_app_min_severity=in_app_min_severity,
        email_min_severity=email_min_severity,
    )

    await db.commit()
    await db.refresh(preference)
    return preference


async def bulk_update_user_notification_preferences(
    *,
    db: AsyncSession,
    user_id: str,
    project_ids: list[UUID],
    notification_type_ids: list[int],
    in_app_enabled: bool | None = None,
    email_enabled: bool | None = None,
    in_app_min_severity: enumerations.NotificationSeverity | None = None,
    email_min_severity: enumerations.NotificationSeverity | None = None,
) -> list[dict[str, Any]]:
    """Update multiple notification preferences in one transaction.

    Args:
        db: Async database session.
        user_id: ID of the user whose preferences are updated.
        project_ids: Project IDs to update preferences for.
        notification_type_ids: Notification type IDs to update.
        in_app_enabled: Override in-app enabled flag, if provided.
        email_enabled: Override email enabled flag, if provided.
        in_app_min_severity: Override in-app minimum severity, if provided.
        email_min_severity: Override email minimum severity, if provided.
    """
    unique_project_ids = list(dict.fromkeys(project_ids))
    unique_notification_type_ids = list(dict.fromkeys(notification_type_ids))

    notification_types_frame = await get_notification_types_query(
        notification_type_ids=unique_notification_type_ids,
    ).get_async(executor=db, output_type=OutputType.PANDAS)
    notification_types_by_id = {
        cast(int, notification_type.notification_type_id): notification_type
        for notification_type in notification_types_frame.itertuples(index=False)
    }
    missing_type_ids = [
        notification_type_id
        for notification_type_id in unique_notification_type_ids
        if notification_type_id not in notification_types_by_id
    ]
    if missing_type_ids:
        raise ValueError(f"Notification types do not exist: {missing_type_ids}")

    upsert_query = upsert_bulk_user_notification_preferences_query(
        user_id=user_id,
        project_ids=unique_project_ids,
        notification_type_ids=unique_notification_type_ids,
        in_app_enabled=in_app_enabled,
        email_enabled=email_enabled,
        in_app_min_severity=in_app_min_severity,
        email_min_severity=email_min_severity,
    )
    updated_preferences_frame = await upsert_query.get_async(
        executor=db,
        output_type=OutputType.PANDAS,
    )
    updated_preferences = normalize_notification_preference_records(
        records=cast(
            list[dict[str, Any]],
            updated_preferences_frame.to_dict(orient="records"),
        ),
    )
    updated_preferences_by_key: dict[tuple[UUID, int], dict[str, Any]] = {
        (
            preference["project_id"],
            preference["notification_type_id"],
        ): dict(preference)
        for preference in updated_preferences
    }
    await db.commit()

    return [
        updated_preferences_by_key[(project_id, notification_type_id)]
        for project_id in unique_project_ids
        for notification_type_id in unique_notification_type_ids
        if (project_id, notification_type_id) in updated_preferences_by_key
    ]
