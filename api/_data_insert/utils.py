import os
from pathlib import Path

import numpy as np
import pandas as pd
from app import settings

CONNECTION_STRING = settings.CONNECTION_STRING
EXCEL_PATH = Path(settings.EXCEL_PATH or "EXCEL_PATH not found!")


def get_df(sheet_name: str, project_name_short: str | None = None) -> pd.DataFrame:
    """
    Get a DataFrame from an Excel file.

    Args:
        sheet_name (str): The name of the sheet to read.
        project_name_short (Optional[str]): The name of the project to read from.

    Returns:
        pd.DataFrame: The cleanedDataFrame.
    """

    if project_name_short:
        file_path = EXCEL_PATH / f"{project_name_short}.xlsx"
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    else:
        file_path = EXCEL_PATH / "_operational.xlsx"
        df = pd.read_excel(file_path, sheet_name=sheet_name)

    df = clean_df(df)

    return df


def get_sheet_names() -> list[str]:
    # Get sheet names from Excel file
    """Get sheet names."""
    sheet_names_raw = pd.ExcelFile(EXCEL_PATH).sheet_names

    # Convert sheet names to list of strings
    sheet_names: list[str] = [str(sheet) for sheet in sheet_names_raw]

    return sheet_names


def clean_df(df: pd.DataFrame, *, index_col: str | None = None) -> pd.DataFrame:
    # If index_col is provided, drop all rows where the index_col is None
    """Handle clean df.

    Args:
        df: TODO: describe.
        index_col: TODO: describe.
    """
    if index_col:
        df = df.dropna(subset=[index_col])

    # Drop all columns that begin with "_"
    df = df.loc[:, ~df.columns.str.startswith("_")]

    # Drop all columns that begin with "Unnamed"
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    # Convert all columns that contain "_id" to integers
    # Missing values are converted to NaNs which force the column to be float
    for col in df.columns:
        if col.endswith("_id"):
            try:
                df[col] = df[col].astype("Int64")
            except ValueError:
                continue

    # Column data type conversions
    for col in df.columns:
        if col in ["in_tsdb", "logical"] or "has_" in col:
            df[col] = df[col].astype(bool)

    # If DataFrame contains tags, drop null tag_ids
    if "tag_id" in df.columns:
        df = df.dropna(subset=["tag_id"])

    # Drop all rows where all values are NaNs
    df = df.dropna(how="all")

    # Replace NaNs with None for Postgres compatibility
    df = df.replace({np.nan: None})

    return df


def get_device_id_path(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates a full path (ancestor chain) for each device in the DataFrame
    by mapping device IDs to their parent device IDs.

    Args:
        df (pd.DataFrame): A DataFrame containing 'device_id' and
            'parent_device_id' columns.

    Returns:
        pd.DataFrame: The original DataFrame with an additional column
            'device_id_path' that contains the full path for each device.
    """
    # Build a map of device_id -> parent_device_id
    parent_map = dict(zip(df["device_id"], df["parent_device_id"]))

    def get_device_path(dev_id, parent_map):
        """Builds the full path (ancestor chain) for a single device
        by following the 'parent_device_id' links.

        Args:
            dev_id: TODO: describe.
            parent_map: TODO: describe.
        """
        path = []
        current_id = dev_id

        while not pd.isna(current_id) and current_id in parent_map:
            path.append(str(int(current_id)))
            current_id = parent_map[current_id]

        if not pd.isna(current_id):
            path.append(str(int(current_id)))

        path.reverse()
        return ".".join(path)

    # Generate the full path for each device
    df["device_id_path"] = df["device_id"].apply(
        lambda x: get_device_path(x, parent_map),
    )

    return df


def application_name(file_path: str) -> str:
    """Handle application name.

    Args:
        file_path: TODO: describe.
    """
    file_name = os.path.basename(file_path)
    file_name = file_name.replace(".py", "")

    return f"data_insert_{file_name}"
