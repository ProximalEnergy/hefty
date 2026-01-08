from typing import Annotated

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
def get_block_dropdown(
    project_db: Annotated[Session, Depends(dependencies.get_project_db)],
):
    """todo

    Args:
        project_db: TODO: describe.
    """
    BLOCK_DEVICE_TYPE_ID = 6

    # Fetch block devices
    blocks = core.crud.project.devices.get_project_devices(
        project_db, device_type_ids=[BLOCK_DEVICE_TYPE_ID]
    ).models()

    # Sort blocks by name_long using natsort
    # NOTE: Update name_long in db if this sort is not working as expected
    blocks = natsorted(blocks, key=lambda x: x.name_long)

    # Add name_full to each block
    blocks_out: list[BlockDropdownItem] = []
    for item in blocks:
        block = BlockDropdownItem(
            device_id=item.device_id, name_full=f"Block {item.name_long}"
        )
        blocks_out.append(block)

    return blocks_out
