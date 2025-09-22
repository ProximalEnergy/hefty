import os
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces
from app._crud.admin.user_subscriptions import (
    get_user_notification_subscriptions as crud_get_user_notification_subscriptions,
)
from app._crud.admin.user_subscriptions import (
    get_user_report_subscriptions as crud_get_user_report_subscriptions,
)
from app._crud.admin.user_subscriptions import (
    get_user_subscriptions as crud_get_user_subscriptions,
)
from app._crud.admin.user_subscriptions import (
    update_user_notification_subscription as crud_update_user_notification_subscription,
)
from app._crud.admin.user_subscriptions import (
    update_user_report_subscription as crud_update_user_report_subscription,
)
from core import models

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


async def get_email_from_clerk(*, user_id: str, api_prod: bool):
    if api_prod:
        clerk_secret = os.environ.get("CLERK_SECRET_KEY")
    else:
        clerk_secret = os.environ.get("CLERK_SECRET_KEY_DEVELOPMENT")

    async with httpx.AsyncClient() as client:
        clerk_response = await client.get(
            f"https://api.clerk.com/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {clerk_secret}"},
        )

    if clerk_response.is_success:
        clerk_data = clerk_response.json()
        primary_email_address_id = clerk_data.get("primary_email_address_id")
        email_address = [
            address["email_address"]
            for address in clerk_data["email_addresses"]
            if address["id"] == primary_email_address_id
        ][0]

        return email_address


@router.get(
    "/",
    response_model=list[interfaces.UserSubscription],
    description="Get all subscriptions for requesting user.",
)
async def get_requesting_user_subscriptions(
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    project_ids = user_data.operational_project_ids

    subscriptions = await crud_get_user_subscriptions(db=db, user_id=user_data.user_id)
    subscription_project_ids = [
        subscription.operational_project_id for subscription in subscriptions
    ]

    for project_id in project_ids:
        if project_id not in subscription_project_ids:
            subscriptions.append(
                models.UserSubscription(
                    user_id=user_data.user_id,
                    operational_project_id=project_id,
                    notifications=False,
                    reports=False,
                ),
            )

    return subscriptions


@router.get(
    "/notifications/{project_id}",
    response_model=list[str],
    dependencies=[Depends(dependencies.requires_superadmin_async)],
    description="""
        Get all emails subscribed to notifications for a project.
        Requires admin permissions.
    """,
)
async def get_notification_emails(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    is_prod_api: Annotated[bool, Depends(dependencies.is_prod_api)],
):
    try:
        subscriptions = await crud_get_user_notification_subscriptions(
            db=db,
            operational_project_id=project_id,
        )

        emails = []

        for subscription in subscriptions:
            email = await get_email_from_clerk(
                user_id=subscription.user_id,
                api_prod=is_prod_api,
            )
            if email:
                emails.append(email)

        return emails

    except Exception:
        raise HTTPException(status_code=400, detail="Failed to get notification emails")


@router.put("/notifications/{project_id}", response_model=interfaces.UserSubscription)
async def update_notification_subscription(
    project_id: UUID,
    data: interfaces.UserSubscriptionUpdate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    try:
        updated_subscription = await crud_update_user_notification_subscription(
            db=db,
            user_id=user_data.user_id,
            operational_project_id=project_id,
            notifications=data.subscribe,
        )
        return updated_subscription
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to update notification subscription",
        )


@router.get(
    "/reports/{project_id}",
    dependencies=[Depends(dependencies.requires_superadmin_async)],
    response_model=list[str],
    description="Get all emails subscribed to reports for a project. ",
)
async def get_report_emails(
    project_id: UUID,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    is_prod_api: Annotated[bool, Depends(dependencies.is_prod_api)],
):
    try:
        subscriptions = await crud_get_user_report_subscriptions(
            db=db,
            operational_project_id=project_id,
        )

        emails = []

        for subscription in subscriptions:
            email = await get_email_from_clerk(
                user_id=subscription.user_id,
                api_prod=is_prod_api,
            )
            if email:
                emails.append(email)

        return emails

    except Exception:
        raise HTTPException(status_code=400, detail="Failed to get report emails")


@router.put("/reports/{project_id}", response_model=interfaces.UserSubscription)
async def update_report_subscription(
    project_id: UUID,
    data: interfaces.UserSubscriptionUpdate,
    db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    try:
        updated_subscription = await crud_update_user_report_subscription(
            db=db,
            user_id=user_data.user_id,
            operational_project_id=project_id,
            reports=data.subscribe,
        )
        return updated_subscription
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Failed to update report subscription",
        )
