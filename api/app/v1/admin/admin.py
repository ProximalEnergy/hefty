import logging
from typing import Annotated

import httpx
from core.db_query import OutputType
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import dependencies, interfaces, settings
from app.v1.admin import (
    api_key,
    companies,
    company_projects,
    notification_preferences,
    notification_types,
    notifications,
    permissions,
    subscriptions,
    teams,
    user_kpi_types,
    user_projects,
    users,
)
from core import crud

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(api_key.router)
router.include_router(permissions.router)
router.include_router(subscriptions.router)
router.include_router(notification_preferences.router)
router.include_router(notification_types.router)
router.include_router(company_projects.router)
router.include_router(companies.router)
router.include_router(teams.router)
router.include_router(users.router)
router.include_router(user_projects.router)
router.include_router(user_kpi_types.router)
router.include_router(notifications.router)


@router.get(
    "/user-type",
    response_model=interfaces.UserType,
)
async def get_user_type(
    _db: Annotated[AsyncSession, Depends(dependencies.get_async_db)],
    user_data: Annotated[
        interfaces.UserData, Depends(dependencies.get_user_data_async)
    ],
):
    """todo

    Args:
        _db: TODO: describe.
        user_data: TODO: describe.
    """
    user_type_id = user_data.user_type_id

    user_type_query = crud.admin.user_types.get_user_type(
        user_type_id=user_type_id,
    )
    user_type = await user_type_query.get_async(output_type=OutputType.SQLALCHEMY)

    return user_type


@router.get("/user-email")
async def get_user_email(
    user_id: str,
    api_prod: Annotated[bool, Depends(dependencies.is_prod_api)],
):
    """todo

    Args:
        user_id: TODO: describe.
        api_prod: TODO: describe.
    """
    try:
        if api_prod:
            clerk_secret = settings.CLERK_SECRET_KEY
        else:
            clerk_secret = settings.CLERK_SECRET_KEY_DEVELOPMENT

        async with httpx.AsyncClient() as client:
            clerk_response = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={"Authorization": f"Bearer {clerk_secret}"},
            )

        clerk_data = clerk_response.json()
        primary_email_address_id = clerk_data.get("primary_email_address_id")
        email_address = [
            address["email_address"]
            for address in clerk_data["email_addresses"]
            if address["id"] == primary_email_address_id
        ][0]
        return email_address
    except Exception:
        logging.error(f"Could not fetch email address for user {user_id}")

    return None


@router.get("/user-emails")
async def get_user_emails(
    api_prod: Annotated[bool, Depends(dependencies.is_prod_api)],
    user_ids: list[str] = Query(default=[]),
):
    """todo

    Args:
        api_prod: TODO: describe.
        user_ids: TODO: describe.
    """
    try:
        if api_prod:
            clerk_secret = settings.CLERK_SECRET_KEY
        else:
            clerk_secret = settings.CLERK_SECRET_KEY_DEVELOPMENT

        async with httpx.AsyncClient() as client:
            clerk_response = await client.get(
                "https://api.clerk.com/v1/users/",
                headers={"Authorization": f"Bearer {clerk_secret}"},
                params={"user_ids": user_ids},
            )

        clerk_data = clerk_response.json()
        primary_email_address_ids = [u["primary_email_address_id"] for u in clerk_data]
        email_addresses = []
        for u in clerk_data:
            if u["primary_email_address_id"] not in primary_email_address_ids:
                continue
            for address in u["email_addresses"]:
                if address["id"] in primary_email_address_ids:
                    email_addresses.append(address["email_address"])
        return email_addresses
    except Exception:
        logging.error("Could not fetch email addresses for requested users.")

    return None
