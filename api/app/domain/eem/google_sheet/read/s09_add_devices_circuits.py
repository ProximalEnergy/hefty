import pandas as pd
from core.db_query import OutputType
from core.enumerations import DeviceTypeEnum
from sqlalchemy.orm import Session

from app import utils
from core import crud


async def add_devices_circuits(
    *,
    project_db: Session,
    system: pd.DataFrame,
) -> pd.DataFrame:
    # --- Get devices from the database ---
    """todo

    Args:
        project_db: Description for project_db.
        system: Description for system.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    blocks = await crud.project.devices.get_project_devices(
        device_type_ids=[DeviceTypeEnum.PV_BLOCK],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    blocks = blocks[["device_id", "parent_device_id"]].rename(
        columns={
            "device_id": "block_device_id",
            "parent_device_id": "circuit_device_id",
        },
    )

    # --- Perform Left Merge ---
    # Merge inverter_device_id into system based on designation matching name_long
    # Use 'left' merge to keep all rows from 'system'
    merged_system = pd.merge(system, blocks, how="left")
    return merged_system
