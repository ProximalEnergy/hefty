from typing import Annotated

from core.crud.operational.failure_modes import get_failure_modes
from core.db_query import OutputType
from fastapi import APIRouter, Query

router = APIRouter(prefix="/failure-modes", tags=["failure-modes"])


@router.get("", operation_id="get_failure_modes")
async def get_failure_modes_route(
    failure_mode_ids: Annotated[list[int], Query()] = [],
):
    """todo

    Args:
        failure_mode_ids: TODO: describe.
    """
    failure_modes_query = get_failure_modes(
        failure_mode_ids=failure_mode_ids,
    )
    failure_modes = await failure_modes_query.get_async(
        output_type=OutputType.PANDAS,
    )
    return failure_modes.to_dict(orient="records")
