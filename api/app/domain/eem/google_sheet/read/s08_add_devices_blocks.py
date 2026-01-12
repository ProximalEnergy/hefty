import pandas as pd
from core.db_query import OutputType
from core.enumerations import DeviceType
from sqlalchemy.orm import Session

import core
from app import utils


async def add_devices_blocks(
    *,
    project_db: Session,
    system: pd.DataFrame,
) -> pd.DataFrame:
    # --- Get devices from the database ---
    """todo

    Args:
        project_db: TODO: describe.
        system: TODO: describe.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    transformers = await core.crud.project.devices.get_project_devices(
        device_type_ids=[DeviceType.MVT],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
    transformers = transformers[["device_id", "parent_device_id"]].rename(
        columns={
            "device_id": "transformer_device_id",
            "parent_device_id": "block_device_id",
        },
    )

    # --- Perform Left Merge ---
    # Merge inverter_device_id into system based on designation matching name_long
    # Use 'left' merge to keep all rows from 'system'
    merged_system = pd.merge(
        system,
        transformers,
        how="left",
    )
    return merged_system
