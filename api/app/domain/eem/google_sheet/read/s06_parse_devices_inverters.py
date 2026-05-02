import pandas as pd
from core.db_query import OutputType
from core.enumerations import DeviceTypeEnum
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import core
from app import utils


async def parse_devices_inverters(
    *,
    project_db: Session,
    system: pd.DataFrame,
):
    # --- Get devices from the database ---
    """todo

    Args:
        project_db: Description for project_db.
        system: Description for system.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    inverters = await core.crud.project.devices.get_project_devices(
        device_type_ids=[DeviceTypeEnum.PV_INVERTER],
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)
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
            f"Validation Error: {num_missing} PCS Number value(s) from the "
            "Google Sheet do not match any inverter "
            "project.devices.name_long value. "
            f"Missing PCS Number value(s): {missing_list_str}"
        )
        numeric_missing = pd.to_numeric(
            pd.Series(missing_designations),
            errors="coerce",
        )
        if (
            numeric_missing.notna().all()
            and (numeric_missing >= 0).all()
            and (numeric_missing < 10).all()
        ):
            error_detail += (
                " Hint: all missing PCS Number values are below 10. "
                "If project.devices.name_long uses zero padding "
                "(for example, '01'), use the same format in the Google Sheet."
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
