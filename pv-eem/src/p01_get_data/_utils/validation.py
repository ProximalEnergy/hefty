# --- Imports ---
import os

import pandas as pd


# --- Function ---
def save_validation_met_data(
    *,
    met_data_pandas: pd.DataFrame,
    project_name_short: str,
    simulation_start: str,
    met_name: str | None = None,
) -> pd.DataFrame:
    """Save met data for validation and clean the data by setting minimum GHI to 0 and
    filling NaNs with 0.

    Args:
        met_data_pandas: The met data DataFrame to process
        project_name_short: Short name of the project for file naming
        simulation_start: Start date string for file naming
        met_name: Optional met name to filter data by. If provided,-
        only data matching this met name will be saved.

    Returns:
        Cleaned met data DataFrame with GHI >= 0 and NaNs filled with 0
    """
    # Create a copy to avoid modifying the original
    cleaned_met_data = met_data_pandas.copy()

    # Filter by met_name if specified
    if met_name is not None and "met_name" in cleaned_met_data.columns:
        cleaned_met_data = cleaned_met_data[cleaned_met_data["met_name"] == met_name]

    # Set minimum GHI to 0 for any GHI-related columns
    ghi_columns = [col for col in cleaned_met_data.columns if "ghi" in col.lower()]
    for ghi_col in ghi_columns:
        cleaned_met_data[ghi_col] = cleaned_met_data[ghi_col].clip(lower=0)

    # Fill all NaNs with 0
    cleaned_met_data = cleaned_met_data.fillna(0)

    # Create directory if it doesn't exist
    output_dir = f"_tests/_artifacts/{project_name_short}/{simulation_start[:10]}"
    os.makedirs(output_dir, exist_ok=True)

    # Save the cleaned data
    cleaned_met_data.to_csv(f"{output_dir}/met_data_{met_name}.csv")

    return cleaned_met_data
