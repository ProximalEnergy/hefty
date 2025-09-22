import logging

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import core


def parse_devices_combiners(
    *,
    project_db: Session,
    system: pd.DataFrame,
):
    # --- Get devices from the database ---
    combiner_models = core.crud.project.devices.get_project_devices(
        db=project_db,
        device_type_ids=[9],
    ).models()
    combiners = pd.DataFrame([x.__dict__ for x in combiner_models])
    combiners = combiners[["name_long", "device_id"]].rename(
        columns={"device_id": "combiner_device_id"},
    )

    # --- Perform Left Merge ---
    # Merge combiner_device_id into system based on designation matching name_long
    # Use 'left' merge to keep all rows from 'system'
    merged_system = pd.merge(
        system,
        combiners,
        left_on="Combiner Designation",
        right_on="name_long",
        how="left",
    )

    # --- Validation Step ---
    # Find rows in the merged result where 'combiner_device_id' is NaN,
    # indicating a 'Combiner Designation' from 'system' was not found in 'combiners'.
    missing_mask = merged_system["combiner_device_id"].isnull()
    missing_designations = merged_system.loc[
        missing_mask,
        "Combiner Designation",
    ].unique()

    if len(missing_designations) > 0:
        # Format the error message
        num_missing = len(missing_designations)
        missing_list_str = ", ".join(
            map(str, missing_designations[:10]),
        )  # Get first 10
        error_detail = (
            f"Validation Error: The following {num_missing} "
            f"Combiner Designation(s) found in the input data do not exist "
            f"in the project's combiner devices: {missing_list_str}"
        )
        if num_missing > 10:
            error_detail += f" (and {num_missing - 10} more)."

        logging.error(f"ERROR: {error_detail}")  # Log the error server-side if needed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail,
        )

    # --- Finalize ---
    # Drop the auxiliary 'name_long' column added during the merge
    merged_system = merged_system.drop(
        columns=[
            "name_long",
            "Combiner Number",
            "Combiner Designation",
        ],
    )
    return merged_system
