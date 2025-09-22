import pandas as pd
from sqlalchemy.orm import Session

import core


def add_devices_circuits(
    *,
    project_db: Session,
    system: pd.DataFrame,
) -> pd.DataFrame:
    # --- Get devices from the database ---
    blocks_list = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[6],  # operational.device_types (6 == block)
    ).models()
    blocks = pd.DataFrame([x.__dict__ for x in blocks_list])
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
