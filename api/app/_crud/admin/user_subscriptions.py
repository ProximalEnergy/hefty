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
