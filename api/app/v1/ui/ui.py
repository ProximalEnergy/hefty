from typing import Annotated

from core.db_query import OutputType
from fastapi import APIRouter, Depends
from natsort import natsorted
from pydantic import BaseModel
from sqlalchemy.orm import Session

import core
from app import dependencies, utils

router = APIRouter(
    prefix="/ui/{project_id}",
    tags=["ui"],
    dependencies=[Depends(dependencies.check_project_access_async)],
    # Do not include these endpoints in the Swagger UI because API users will
    # never access
    # them directly
    include_in_schema=utils.get_include_in_schema(),
)


class BlockDropdownItem(BaseModel):
    """todo"""

    device_id: int
    name_full: str


# NOTE: This endpoint might be able to be replaced with the general GET /devices
# endpoint once name_full is supported. Custom hook in the web-app would need to
# be updated as well.
@router.get(
    "/block-dropdown",
    response_model=list[BlockDropdownItem],
    description="Get a list of blocks sorted by name",
)
async def get_block_dropdown(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """todo

    Args:
        project_db: TODO: describe.
    """
    BLOCK_DEVICE_TYPE_ID = 6

    # Fetch block devices
    project_schema = utils.get_project_schema(project_db=project_db)
    blocks_df = await core.crud.project.devices.get_project_devices(
        device_type_ids=[BLOCK_DEVICE_TYPE_ID]
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    blocks_df = blocks_df.copy()
    blocks_df["name_long"] = blocks_df["name_long"].fillna("")

    # Sort blocks by name_long using natsort
    # NOTE: Update name_long in db if this sort is not working as expected
    blocks = natsorted(
        blocks_df.to_dict("records"),
        key=lambda x: x.get("name_long") or "",
    )

    # Add name_full to each block
    blocks_out: list[BlockDropdownItem] = []
    for item in blocks:
        block = BlockDropdownItem(
            device_id=int(item["device_id"]),
            name_full=f"Block {item.get('name_long')}",
        )
        blocks_out.append(block)

    return blocks_out
