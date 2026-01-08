from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import enumerations, models


async def get_user_notification_preferences(
    *,
    db: AsyncSession,
    user_id: str,
    project_ids: list[UUID] | None = None,
) -> list[models.NotificationPreference]:
    """Get notification preferences for a user.

    Args:
        db: Database session.
        user_id: User ID.
        project_ids: Optional list of project IDs to filter by.
    """
    query = select(models.NotificationPreference).where(
        models.NotificationPreference.user_id == user_id
    )
    if project_ids:
        query = query.where(models.NotificationPreference.project_id.in_(project_ids))
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_notification_preference(
    *,
    db: AsyncSession,
    user_id: str,
    project_id: UUID,
    notification_type_id: int,
) -> models.NotificationPreference | None:
    """Get a specific notification preference.

    Args:
        db: Database session.
        user_id: User ID.
        project_id: Project ID.
        notification_type_id: Notification type ID.
    """
    query = select(models.NotificationPreference).where(
        models.NotificationPreference.user_id == user_id,
        models.NotificationPreference.project_id == project_id,
        models.NotificationPreference.notification_type_id == notification_type_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


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
    # Try to get existing preference
    preference = await get_user_notification_preference(
        db=db,
        user_id=user_id,
        project_id=project_id,
        notification_type_id=notification_type_id,
    )

    if preference is not None:
        return preference

    # Get notification type for defaults
    query = select(models.NotificationType).where(
        models.NotificationType.notification_type_id == notification_type_id
    )
    result = await db.execute(query)
    notification_type = result.scalar_one_or_none()
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

    if in_app_enabled is not None:
        preference.in_app_enabled = in_app_enabled
    if email_enabled is not None:
        preference.email_enabled = email_enabled
    if in_app_min_severity is not None:
        preference.in_app_min_severity = in_app_min_severity
    if email_min_severity is not None:
        preference.email_min_severity = email_min_severity

    await db.commit()
    await db.refresh(preference)
    return preference
