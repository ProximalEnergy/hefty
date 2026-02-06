from typing import Literal
from uuid import UUID

from core.db_query import DbQuery, OutputType
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_user_subscriptions(
    *,
    db: AsyncSession,
    user_id: str,
) -> list:
    """Get all subscriptions for a user.

    Args:
        db: Database session.
        user_id: User identifier to filter subscriptions.
    """
    query = select(models.UserSubscription).where(
        models.UserSubscription.user_id == user_id
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_notification_subscriptions(
    *,
    db: AsyncSession,
    operational_project_id: UUID,
):
    """Get notification-enabled subscriptions for a project.

    Args:
        db: Database session.
        operational_project_id: Project identifier to filter subscriptions.
    """
    query = select(models.UserSubscription).where(
        models.UserSubscription.operational_project_id == operational_project_id,
        models.UserSubscription.notifications,
    )
    result = await db.execute(query)
    return result.scalars().all()


async def update_user_notification_subscription(
    *,
    db: AsyncSession,
    user_id: str,
    operational_project_id: UUID,
    notifications: bool,
):
    """Update or create a notification subscription.

    Args:
        db: Database session.
        user_id: User identifier to update.
        operational_project_id: Project identifier to update.
        notifications: New notification state.
    """
    try:
        # Try to get the existing subscription
        query = select(models.UserSubscription).where(
            models.UserSubscription.user_id == user_id,
            models.UserSubscription.operational_project_id == operational_project_id,
        )
        result = await db.execute(query)
        subscription = result.scalar_one()

        # Update the notifications value
        subscription.notifications = notifications
        await db.commit()
        await db.refresh(subscription)
        return subscription
    except NoResultFound:
        # Create a new subscription if it doesn't exist
        new_subscription = models.UserSubscription(
            user_id=user_id,
            operational_project_id=operational_project_id,
            notifications=notifications,
        )
        db.add(new_subscription)
        await db.commit()
        await db.refresh(new_subscription)
        return new_subscription


async def get_user_report_subscriptions(
    *,
    db: AsyncSession,
    operational_project_id: UUID,
):
    """Get report-enabled subscriptions for a project.

    Args:
        db: Database session.
        operational_project_id: Project identifier to filter subscriptions.
    """
    query = select(models.UserSubscription).where(
        models.UserSubscription.operational_project_id == operational_project_id,
        models.UserSubscription.reports,
    )
    result = await db.execute(query)
    return result.scalars().all()


async def update_user_report_subscription(
    *,
    db: AsyncSession,
    user_id: str,
    operational_project_id: UUID,
    reports: bool,
):
    """Update or create a report subscription.

    Args:
        db: Database session.
        user_id: User identifier to update.
        operational_project_id: Project identifier to update.
        reports: New report state.
    """
    try:
        # Try to get the existing subscription
        query = select(models.UserSubscription).where(
            models.UserSubscription.user_id == user_id,
            models.UserSubscription.operational_project_id == operational_project_id,
        )
        result = await db.execute(query)
        subscription = result.scalar_one()

        # Update the reports value
        subscription.reports = reports
        await db.commit()
        await db.refresh(subscription)
        return subscription
    except NoResultFound:
        # Create a new subscription if it doesn't exist
        new_subscription = models.UserSubscription(
            user_id=user_id,
            operational_project_id=operational_project_id,
            reports=reports,
        )
        db.add(new_subscription)
        await db.commit()
        await db.refresh(new_subscription)
        return new_subscription


def get_user_event_chat_notification_subscription(
    *,
    user_id: str,
    operational_project_id: UUID,
) -> DbQuery[models.UserSubscription, Literal[True]]:
    """Get user's event chat notification subscription for a project.
        Returns None if subscription doesn't exist (defaults to True per model).

    Args:
        user_id: The ID of the user.
        operational_project_id: The ID of the operational project.
    """
    query = select(models.UserSubscription).where(
        models.UserSubscription.user_id == user_id,
        models.UserSubscription.operational_project_id == operational_project_id,
    )
    return DbQuery(query=query, is_scalar=True)


async def is_event_chat_notification_enabled(
    *,
    user_id: str,
    operational_project_id: UUID,
) -> bool:
    """Check if event chat notifications are enabled for a user/project.
        Defaults to True if no subscription exists (per model server_default).

    Args:
        user_id: User identifier to check.
        operational_project_id: Project identifier to check.
    """
    subscription = await get_user_event_chat_notification_subscription(
        user_id=user_id,
        operational_project_id=operational_project_id,
    ).get_async(output_type=OutputType.SQLALCHEMY)
    if subscription is None:
        return True  # Default to enabled per model
    return subscription.event_chat_notifications


async def update_user_event_chat_notification_subscription(
    *,
    db: AsyncSession,
    user_id: str,
    operational_project_id: UUID,
    event_chat_notifications: bool,
):
    """Update or create event chat notification subscription.

    Args:
        db: Database session.
        user_id: User identifier to update.
        operational_project_id: Project identifier to update.
        event_chat_notifications: New event chat notification state.
    """
    try:
        # Try to get the existing subscription
        query = select(models.UserSubscription).where(
            models.UserSubscription.user_id == user_id,
            models.UserSubscription.operational_project_id == operational_project_id,
        )
        result = await db.execute(query)
        subscription = result.scalar_one()

        # Update the event_chat_notifications value
        subscription.event_chat_notifications = event_chat_notifications
        await db.commit()
        await db.refresh(subscription)
        return subscription
    except NoResultFound:
        # Create a new subscription if it doesn't exist
        new_subscription = models.UserSubscription(
            user_id=user_id,
            operational_project_id=operational_project_id,
            event_chat_notifications=event_chat_notifications,
        )
        db.add(new_subscription)
        await db.commit()
        await db.refresh(new_subscription)
        return new_subscription


async def get_event_chat_notification_statuses_batch(
    *,
    db: AsyncSession,
    user_id: str,
    operational_project_ids: list[UUID],
) -> dict[UUID, bool]:
    """Get event chat notification statuses for multiple projects.

        Returns a dictionary mapping project_id -> enabled status.
        Defaults to True if no subscription exists (per model server_default).

    Args:
        db: Database session.
        user_id: User identifier to check.
        operational_project_ids: Project identifiers to check.
    """
    if not operational_project_ids:
        return {}

    query = select(models.UserSubscription).where(
        models.UserSubscription.user_id == user_id,
        models.UserSubscription.operational_project_id.in_(operational_project_ids),
    )
    result = await db.execute(query)
    subscriptions = result.scalars().all()

    # Create a map of project_id -> enabled status
    status_map: dict[UUID, bool] = {}

    # Initialize all projects as enabled (default)
    for project_id in operational_project_ids:
        status_map[project_id] = True

    # Update with actual subscription values
    for subscription in subscriptions:
        status_map[subscription.operational_project_id] = (
            subscription.event_chat_notifications
        )

    return status_map


async def update_event_chat_notification_statuses_batch(
    *,
    db: AsyncSession,
    user_id: str,
    project_statuses: dict[UUID, bool],
) -> dict[UUID, bool]:
    """Update event chat notification statuses for multiple projects in a
    single transaction.

    Args:
        db: Database session
        user_id: User ID
        project_statuses: Dictionary mapping project_id -> enabled status

    Returns:
        Dictionary mapping project_id -> enabled status (updated values)
    """
    if not project_statuses:
        return {}

    # Get existing subscriptions for these projects
    query = select(models.UserSubscription).where(
        models.UserSubscription.user_id == user_id,
        models.UserSubscription.operational_project_id.in_(
            list(project_statuses.keys())
        ),
    )
    result = await db.execute(query)
    existing_subscriptions = {
        sub.operational_project_id: sub for sub in result.scalars().all()
    }

    # Update or create subscriptions
    updated_statuses: dict[UUID, bool] = {}
    for project_id, enabled in project_statuses.items():
        if project_id in existing_subscriptions:
            # Update existing subscription
            subscription = existing_subscriptions[project_id]
            subscription.event_chat_notifications = enabled
        else:
            # Create new subscription
            new_subscription = models.UserSubscription(
                user_id=user_id,
                operational_project_id=project_id,
                event_chat_notifications=enabled,
            )
            db.add(new_subscription)
            existing_subscriptions[project_id] = new_subscription

        updated_statuses[project_id] = enabled

    await db.commit()

    # Refresh all subscriptions
    for subscription in existing_subscriptions.values():
        await db.refresh(subscription)

    return updated_statuses
