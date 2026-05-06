import pandas as pd
from fastapi import HTTPException, status

MET_NAME_COLUMN = "Met Name"


def _validate_met_name_column(*, system: pd.DataFrame) -> None:
    """Require Met Name values before building the S3 system file.

    Args:
        system: Google Sheet Input tab data before system file formatting.
    """
    if MET_NAME_COLUMN not in system.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Google Sheet Input tab is missing the 'Met Name' column. "
                "Add the column or use Map Inverters to Met Stations before "
                "updating the System S3 file."
            ),
        )

    met_names = system[MET_NAME_COLUMN]
    blank_met_name_mask = met_names.isna() | met_names.astype(str).str.strip().eq("")
    if not blank_met_name_mask.any():
        return

    blank_rows = blank_met_name_mask[blank_met_name_mask]
    blank_row_numbers = (blank_rows.index + 2).tolist()
    if len(blank_row_numbers) == len(system):
        detail = (
            "Google Sheet Input tab has an empty 'Met Name' column. Use "
            "Map Inverters to Met Stations before updating the System S3 file, "
            "or manually fill Met Name for each row."
        )
    else:
        visible_rows = ", ".join(map(str, blank_row_numbers[:10]))
        detail = (
            "Google Sheet Input tab has blank 'Met Name' values in row(s): "
            f"{visible_rows}. Use Map Inverters to Met Stations before "
            "updating the System S3 file, or manually fill those rows."
        )
        if len(blank_row_numbers) > 10:
            detail += f" ({len(blank_row_numbers) - 10} more)."

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail,
    )


def build_system(
    *,
    system: pd.DataFrame,
):
    # --- hardcoded ---
    """todo

    Args:
        system: Description for system.
    """
    _validate_met_name_column(system=system)

    system["string_id"] = range(len(system))
    system["racking_device_id"] = -999
    system["pcs_module_id"] = -999
    system["transformer_equipment_id"] = -999

    # --- Define the renaming dictionary ---
    rename_mapping = {
        "combiner_device_id": "combiner_device_id",
        "pv_module_id": "module_equipment_id",
        "Modules per Strings": "modules_per_string",
        "Strings per Combiner": "strings_per_combiner",
        "racking_id": "racking_equipment_id",
        "GCR": "racking_controls_gcr",
        "DC Line to Combiner at STC": "dc_line_to_combiner_stc",
        "DC Line to Inverter at STC": "dc_line_to_inverter_stc",
        "inverter_device_id": "pcs_device_id",
        "inverter_equipment_id": "pcs_equipment_id",
        "Met Name": "met_name",
    }
    system = system.rename(columns=rename_mapping)

    # Define the desired column order (exactly as shown in the image, ignoring spaces)
    desired_column_order = [
        "string_id",
        "module_equipment_id",
        "modules_per_string",
        "strings_per_combiner",
        "dc_line_to_combiner_stc",
        "combiner_device_id",
        "racking_controls_gcr",
        "racking_equipment_id",
        "racking_device_id",
        "pcs_module_id",
        "dc_line_to_inverter_stc",
        "pcs_equipment_id",
        "pcs_device_id",
        "transformer_equipment_id",
        "transformer_device_id",
        "block_device_id",
        "circuit_device_id",
        "met_name",
    ]

    # Create a new DataFrame with columns in the desired order
    system = system[desired_column_order]

    # --- Set specific types ---

    # Define columns that should be float type
    float_columns = [
        "modules_per_string",
        "strings_per_combiner",
        "racking_controls_gcr",
        "dc_line_to_combiner_stc",
        "dc_line_to_inverter_stc",
    ]

    # Convert all float columns at once
    system[float_columns] = system[float_columns].astype(float)

    return system
