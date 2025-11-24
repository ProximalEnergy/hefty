from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_user_subscriptions(
    *,
    db: AsyncSession,
    user_id: str,
) -> list:
    query = select(models.UserSubscription).filter(
        models.UserSubscription.user_id == user_id
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_notification_subscriptions(
    *,
    db: AsyncSession,
    operational_project_id: UUID,
):
    query = select(models.UserSubscription).filter(
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
    try:
        # Try to get the existing subscription
        query = select(models.UserSubscription).filter(
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
    query = select(models.UserSubscription).filter(
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
    try:
        # Try to get the existing subscription
        query = select(models.UserSubscription).filter(
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


async def get_user_event_chat_notification_subscription(
    *,
    db: AsyncSession,
    user_id: str,
    operational_project_id: UUID,
) -> models.UserSubscription | None:
    """Get user's event chat notification subscription for a project.
    Returns None if subscription doesn't exist (defaults to True per model).
    """
    query = select(models.UserSubscription).filter(
        models.UserSubscription.user_id == user_id,
        models.UserSubscription.operational_project_id == operational_project_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def is_event_chat_notification_enabled(
    *,
    db: AsyncSession,
    user_id: str,
    operational_project_id: UUID,
) -> bool:
    """Check if event chat notifications are enabled for a user/project.
    Defaults to True if no subscription exists (per model server_default).
    """
    subscription = await get_user_event_chat_notification_subscription(
        db=db, user_id=user_id, operational_project_id=operational_project_id
    )
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
    """Update or create event chat notification subscription."""
    try:
        # Try to get the existing subscription
        query = select(models.UserSubscription).filter(
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
