import logging
import uuid
from typing import Annotated

from core.crud.admin.users import get_user_by_id
from core.crud.operational.projects import get_projects
from core.db_query import OutputType
from core.utils.user_management import get_user_email_from_clerk
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.admin.companies import get_companies
from app._crud.operational.drone_integrations import (
    create_drone_integration,
    delete_drone_integration,
    get_drone_integrations,
    update_drone_integration,
)
from app._dependencies.authentication import get_user as get_user_auth
from app._utils.user_management import send_drone_inspection_order_email
from app.dependencies import (
    get_async_db,
    requires_superadmin_async,
)
from app.domain.drones.zeitview_parser import ZeitviewAPI
from app.interfaces import (
    DroneIntegrationCreate,
    DroneIntegrationInterface,
    DroneIntegrationUpdate,
    UserAuthed,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/drone-integrations",
    tags=["drone-integrations"],
)


class DroneInspectionOrderRequest(BaseModel):
    """todo"""

    project_id: uuid.UUID
    provider_email: str
    timing: str


class QueryProviderSitesRequest(BaseModel):
    """todo"""

    api_key: str
    provider_id: int


class ProviderSite(BaseModel):
    """todo"""

    provider_site_id: str
    name: str


@router.get("", response_model=list[DroneIntegrationInterface])
async def get_drone_integrations_(
    db: AsyncSession = Depends(get_async_db),
):
    """Get all drone integrations.

    Args:
        db: Description for db.
    """
    return await get_drone_integrations(db=db)


@router.post(
    "",
    response_model=DroneIntegrationInterface,
    dependencies=[Depends(requires_superadmin_async)],
)
async def create_drone_integration_(
    drone_integration: DroneIntegrationCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new drone integration.

    Args:
        drone_integration: Description for drone_integration.
        db: Description for db.
    """
    return await create_drone_integration(db=db, drone_integration=drone_integration)


@router.put(
    "/{drone_integration_id}",
    response_model=DroneIntegrationInterface,
    dependencies=[Depends(requires_superadmin_async)],
)
async def update_drone_integration_(
    drone_integration_id: int,
    drone_integration: DroneIntegrationUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """Update a drone integration.

    Args:
        drone_integration_id: Description for drone_integration_id.
        drone_integration: Description for drone_integration.
        db: Description for db.
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
    """Delete a drone integration.

    Args:
        drone_integration_id: Description for drone_integration_id.
        db: Description for db.
    """
    await delete_drone_integration(db=db, drone_integration_id=drone_integration_id)
    return HTTPException(status_code=200, detail="Drone integration deleted")


@router.post("/order-inspection")
async def order_drone_inspection(
    request: DroneInspectionOrderRequest,
    user_data: Annotated[UserAuthed, Depends(get_user_auth)],
    db: AsyncSession = Depends(get_async_db),
):
    """Send a drone inspection order email to the provider.

    Args:
        request: Description for request.
        user_data: Description for user_data.
        db: Description for db.
    """
    try:
        # Get project information
        db_query = get_projects(project_ids=[request.project_id])
        rows = await db_query.get_async(output_type=OutputType.SQLALCHEMY)
        if not rows:
            raise HTTPException(status_code=404, detail="Project not found")
        project_name = rows[0].name_long

        # Get company information
        companies = await get_companies(db=db, company_ids=[user_data.company_id])
        if not companies:
            raise HTTPException(status_code=404, detail="Company not found")
        company = companies[0]

        # Get user details for the email
        user = await get_user_by_id(user_id=user_data.user_id).get_async(
            output_type=OutputType.SQLALCHEMY
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user email from Clerk
        user_email = await get_user_email_from_clerk(user_id=user_data.user_id)
        if not user_email:
            raise HTTPException(status_code=404, detail="User email not found")

        # Send the email
        await send_drone_inspection_order_email(
            provider_email=request.provider_email,
            user_email=user_email,
            user_name=user.name_long or "Unknown",
            company_name=company.name_long,
            project_name=project_name,
            timing=request.timing,
        )

        return {"message": "Drone inspection order email sent successfully"}

    except Exception as e:
        logger.error(f"Error sending drone inspection order email: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to send drone inspection order email"
        )


@router.post(
    "/query-provider-sites",
    response_model=list[ProviderSite],
    dependencies=[Depends(requires_superadmin_async)],
)
async def query_provider_sites(
    request: QueryProviderSitesRequest,
):
    """Query sites from a drone provider using an API key.
        Currently supports Zeitview (provider_id = 0).

    Args:
        request: Description for request.
    """
    if request.provider_id == 0:
        client = ZeitviewAPI(api_key=request.api_key)
        response = await client.query_sites()
        sites = response.get("data", [])
        return [
            ProviderSite(
                provider_site_id=str(site.get("site_id")),
                name=site.get("site_name", "Unknown"),
            )
            for site in sites
        ]
    else:
        raise HTTPException(status_code=400, detail="Unsupported provider")
