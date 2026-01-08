import uuid
from typing import Annotated

from core.crud.operational.projects import get_projects
from core.db_query import OutputType
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
from app.domain.drones.zeitview_parser import ZeitviewAPI
from app.interfaces import (
    DroneIntegration,
    DroneIntegrationCreate,
    DroneIntegrationUpdate,
    UserData,
)
from app.logger import logger

router = APIRouter(prefix="/drone-integrations")


class DroneInspectionOrderRequest(BaseModel):
    """todo"""

    project_id: uuid.UUID
    provider_email: str
    timing: str


class QueryProviderSitesRequest(BaseModel):
    """todo"""

    api_key: str
    provider_id: int

    model_config = {"extra": "forbid"}


class ProviderSite(BaseModel):
    """todo"""

    site_name: str | None = None
    site_uuid: str
    site_id: int | None = None


@router.get("", response_model=list[DroneIntegration])
async def get_drone_integrations_(
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve all drone integrations.

    Args:
        db: TODO: describe.
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
    """Create a new drone integration.

    Args:
        drone_integration: TODO: describe.
        db: TODO: describe.
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
    """Update a drone integration.

    Args:
        drone_integration_id: TODO: describe.
        drone_integration: TODO: describe.
        db: TODO: describe.
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
        drone_integration_id: TODO: describe.
        db: TODO: describe.
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
    """Send a drone inspection order email to the provider.

    Args:
        request: TODO: describe.
        user_data: TODO: describe.
        db: TODO: describe.
        api_prod: TODO: describe.
    """
    try:
        # Get project information
        db_query = get_projects(project_ids=[request.project_id])
        df = await db_query.get_async(output_type=OutputType.PANDAS)

        if df.empty:
            raise HTTPException(status_code=404, detail="Project not found")

        project_name = df.iloc[0]["name_long"]

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
        request: TODO: describe.
    """
    logger.info(
        f"Query provider sites request: provider_id={request.provider_id}, "
        f"api_key_length={len(request.api_key) if request.api_key else 0}"
    )

    if not request.api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    if request.provider_id != 0:  # Zeitview
        logger.warning(
            f"Unsupported provider_id {request.provider_id} requested. "
            "Only provider_id=0 (Zeitview) is supported."
        )
        raise HTTPException(
            status_code=400,
            detail=f"Provider {request.provider_id} is not yet supported for site querying. Only provider_id=0 (Zeitview) is supported.",
        )

    try:
        # Create a temporary ZeitviewAPI instance with the provided API key
        zeitview_api = ZeitviewAPI.from_api_key(api_key=request.api_key)
        sites_data = await zeitview_api.query_sites()

        # Parse the response
        sites = []
        for site in sites_data.get("data", []):
            sites.append(
                ProviderSite(
                    site_name=site.get("site_name"),
                    site_uuid=site.get("site_uuid", ""),
                    site_id=site.get("site_id"),
                )
            )

        return sites
    except ValueError as e:
        # This catches errors from ZeitviewAPI init or API validation
        logger.error(f"Validation error querying provider sites: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error querying provider sites: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to query provider sites: {str(e)}"
        )
