import pandas as pd
from core.enumerations import DeviceType
from sqlalchemy.orm import Session

import core


def add_devices_blocks(
    *,
    project_db: Session,
    system: pd.DataFrame,
) -> pd.DataFrame:
    # --- Get devices from the database ---
    transformers_data = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[DeviceType.MVT],
    ).models()
    transformers = pd.DataFrame([x.__dict__ for x in transformers_data])
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
