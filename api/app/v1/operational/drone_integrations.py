import uuid
from typing import Annotated

from core.crud.operational.projects import get_project_async
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.admin.companies import get_companies
from app._crud.admin.users import get_user
from app._crud.operational.drone_integrations import (
    create_drone_integration,
    delete_drone_integration,
    get_drone_integrations,
    update_drone_integration,
)
from app._utils.user_management import (
    get_user_email_from_clerk,
    send_drone_inspection_order_email,
)
from app.dependencies import (
    get_async_db,
    get_user_data_async,
    is_prod_origin,
    requires_superadmin_async,
)
from app.interfaces import (
    DroneIntegration,
    DroneIntegrationCreate,
    DroneIntegrationUpdate,
    UserData,
)
from app.logger import logger

router = APIRouter(prefix="/drone-integrations")


class DroneInspectionOrderRequest(BaseModel):
    project_id: uuid.UUID
    provider_email: str
    timing: str


@router.get("", response_model=list[DroneIntegration])
async def get_drone_integrations_(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve all drone integrations.
    """
    return await get_drone_integrations(db=db)


@router.post(
    "",
    response_model=DroneIntegration,
    dependencies=[Depends(requires_superadmin_async)],
)
async def create_drone_integration_(
    drone_integration: DroneIntegrationCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new drone integration.
    """
    return await create_drone_integration(db=db, drone_integration=drone_integration)


@router.put(
    "/{drone_integration_id}",
    response_model=DroneIntegration,
    dependencies=[Depends(requires_superadmin_async)],
)
async def update_drone_integration_(
    drone_integration_id: int,
    drone_integration: DroneIntegrationUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update a drone integration.
    """
    return await update_drone_integration(
        db=db,
        drone_integration_id=drone_integration_id,
        drone_integration=drone_integration,
    )


@router.delete(
    "/{drone_integration_id}", dependencies=[Depends(requires_superadmin_async)]
)
async def delete_drone_integration_(
    drone_integration_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete a drone integration.
    """
    await delete_drone_integration(db=db, drone_integration_id=drone_integration_id)
    return HTTPException(status_code=200, detail="Drone integration deleted")


@router.post("/order-inspection")
async def order_drone_inspection(
    request: DroneInspectionOrderRequest,
    user_data: Annotated[UserData, Depends(get_user_data_async)],
    db: AsyncSession = Depends(get_async_db),
    api_prod: bool = Depends(is_prod_origin),
):
    """
    Send a drone inspection order email to the provider.
    """
    try:
        # Get project information
        project = await get_project_async(db=db, project_id=request.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get company information
        companies = await get_companies(db=db, company_ids=[user_data.company_id])
        if not companies:
            raise HTTPException(status_code=404, detail="Company not found")
        company = companies[0]

        # Get user information for email
        user = await get_user(db=db, user_id=user_data.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user email from Clerk
        user_email = await get_user_email_from_clerk(
            user_id=user_data.user_id, api_prod=api_prod
        )
        if not user_email:
            raise HTTPException(status_code=404, detail="User email not found")

        # Send the email
        await send_drone_inspection_order_email(
            provider_email=request.provider_email,
            user_email=user_email,
            user_name=user.name_long,
            company_name=company.name_long,
            project_name=project.name_long,
            timing=request.timing,
        )

        return {"message": "Drone inspection order email sent successfully"}

    except Exception as e:
        logger.error(f"Error sending drone inspection order email: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to send drone inspection order email"
        )
