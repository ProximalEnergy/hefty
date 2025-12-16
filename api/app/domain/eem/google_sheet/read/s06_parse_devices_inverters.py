import pandas as pd
from core.enumerations import DeviceType
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import core


def parse_devices_inverters(
    *,
    project_db: Session,
    system: pd.DataFrame,
):
    # --- Get devices from the database ---
    """todo

    Args:
        project_db: TODO: describe.
        system: TODO: describe.
    """
    inverter_models = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[DeviceType.PV_PCS],
    ).models()
    inverters = pd.DataFrame([x.__dict__ for x in inverter_models])
    inverters = inverters[["name_long", "device_id", "parent_device_id"]].rename(
        columns={
            "device_id": "inverter_device_id",
            "parent_device_id": "transformer_device_id",
        },
    )

    # --- Perform Left Merge ---
    # Merge inverter_device_id into system based on designation matching name_long
    # Use 'left' merge to keep all rows from 'system'
    merged_system = pd.merge(
        system,
        inverters,
        left_on="PCS Number",
        right_on="name_long",
        how="left",
    )

    # --- Validation Step ---
    # Find rows in the merged result where 'inverter_device_id' is NaN,
    # indicating a 'Inverter Designation' from 'system' was not found in 'inverters'.
    missing_mask = merged_system["inverter_device_id"].isnull()
    missing_designations = merged_system.loc[missing_mask, "PCS Number"].unique()

    if len(missing_designations) > 0:
        # Format the error message
        num_missing = len(missing_designations)
        missing_list_str = ", ".join(
            map(str, missing_designations[:10]),
        )  # Get first 10
        error_detail = (
            f"Validation Error: The following {num_missing} "
            f"Inverter Designation(s) found in the input data do not exist "
            f"in the project's inverter devices: {missing_list_str}"
        )
        if num_missing > 10:
            error_detail += f" (and {num_missing - 10} more)."

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail,
        )

    # --- Finalize ---
    # Drop the auxiliary 'name_long' column added during the merge
    merged_system = merged_system.drop(columns=["name_long", "PCS Number"])
    return merged_system
