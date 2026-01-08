from typing import Annotated

from core.crud.operational.device_types import get_device_types
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app._crud.operational.failure_modes import get_root_causes as crud_get_root_causes
from app.dependencies import get_async_db

router = APIRouter(prefix="/root-causes", tags=["root-causes"])


@router.get("", operation_id="get_root_causes")
async def get_root_causes(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    *,
    root_cause_ids: Annotated[list[int], Query()] = [],
    device_type_ids: Annotated[list[int], Query()] = [],
):
    """Retrieve root causes with optional filtering by IDs and device types.

    This endpoint returns a list of root causes, optionally filtered by
    specific root cause IDs and/or device type IDs. Each root cause is enriched
    with a 'name_full' field that combines the device type name and root cause
    name.

    Args:
        db (Session): Database session dependency
        root_cause_ids (List[int], optional): List of specific root cause IDs
            to filter by. If empty, returns all root causes.
        device_type_ids (List[int], optional): List of device type IDs to
            filter by. If empty, returns root causes for all device types.

    Returns:
        List[dict]: List of root cause dictionaries, each containing:
            - All original root cause attributes
            - name_full (str): Combined string of device type name and root cause name
    """
    root_causes = await crud_get_root_causes(
        db=db,
        root_cause_ids=root_cause_ids,
        device_type_ids=device_type_ids,
    )
    device_types = await get_device_types(
        db=db,
        device_type_ids=device_type_ids,
        only_included_by_default=False,
    )
    device_types_zip = {
        device_type.device_type_id: device_type.name_long
        for device_type in device_types
    }
    root_cause_to_name_full = {
        root_cause.root_cause_id: device_types_zip[root_cause.device_type_id]
        + " "
        + root_cause.name_long
        for root_cause in root_causes
    }
    root_causes = [
        {
            **root_cause.__dict__,
            "name_full": root_cause_to_name_full[root_cause.root_cause_id],
        }
        for root_cause in root_causes
    ]

    return root_causes
