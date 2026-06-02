from typing import Annotated

from core.db_query import OutputType
from fastapi import APIRouter, Query

from app import interfaces
from app._crud.operational.bess_strings import get_bess_strings as crud_get_bess_strings

router = APIRouter(prefix="/bess-strings", tags=["bess_strings"])


@router.get(
    "",
    response_model=list[interfaces.BESSStringInterface],
    operation_id="get_bess_strings",
)
async def get_bess_strings_route(
    *,
    bess_string_ids: Annotated[list[int], Query()] = [],
    device_model_ids: Annotated[list[int], Query()] = [],
) -> list[interfaces.BESSStringInterface]:
    """Get BESS string equipment specifications.

    Args:
        bess_string_ids: Optional BESS string IDs to filter by.
        device_model_ids: Optional device model IDs to filter by.
    """
    rows = await crud_get_bess_strings(
        bess_string_ids=bess_string_ids or None,
        device_model_ids=device_model_ids or None,
    ).get_async(output_type=OutputType.SQLALCHEMY)
    return [interfaces.BESSStringInterface.model_validate(row) for row in rows]
