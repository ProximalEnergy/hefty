import pandas as pd


def build_system(
    *,
    system: pd.DataFrame,
):
    # --- hardcoded ---
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
