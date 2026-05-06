import base64
import json
import logging
from typing import Any

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

from app import settings

# --- Config ---
# Google sheet parameters
# Google service account can be managed through the google cloud console
GSHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
GSHEET_IMPORTANT_COLUMNS = [
    "Module Manufacturer",
    "Module Model",
    "Module Wattage",
    "Modules per Strings",
    "Racking Manufacturer",
    "Racking Model",
    "GCR",
    "Strings per Combiner",
    "Modules",
    "Combiner Number",
    "Combiner Designation",
    "Combiner Power",
    "DC Line to Combiner at STC",
    "DC Line to Inverter at STC",
    "Block Number",
    "Cabinet Number",
    "PCS Number",
    "PCS Manufacturer",
    "PCS Model",
    "Met Name",
]


def _column_index_to_letter(*, index: int) -> str:
    """Convert a 0-based column index to Excel-style
        column letter (A, B, C, ..., Z, AA, AB, etc.)

    Args:
        index: Description for index.
    """
    result = ""
    while index >= 0:
        result = chr(65 + (index % 26)) + result
        index = index // 26 - 1
    return result


def _build_google_sheets_service() -> Any:
    """Build an authenticated Google Sheets service client."""
    credentials = None
    encoded_credentials = settings.COMMISSIONING_KEY_JSON
    if encoded_credentials:
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
        service_account_info = json.loads(decoded_credentials)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=GSHEET_SCOPES,
        )
    else:
        raise ValueError("Google sheet credentials not found in env")

    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def read_google_sheet(
    *,
    spreadsheet_id: str,
    end_column_name: str = GSHEET_IMPORTANT_COLUMNS[-1],
) -> pd.DataFrame:
    # Authenticate using the service account key
    """todo

    Args:
        spreadsheet_id: Description for spreadsheet_id.
        end_column_name: Description for end_column_name.
    """
    try:
        service = _build_google_sheets_service()

        # --- Example Operations ---

        # 1. First, read the header row to find the end column
        header_range = "Input!1:1"
        header_result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=header_range)
            .execute()
        )
        header_values = header_result.get("values", [])

        if not header_values or not header_values[0]:
            raise ValueError("No header row found in the sheet")

        headers = header_values[0]

        # Find the end column by name
        try:
            end_column_index = headers.index(end_column_name)
            end_column_letter = _column_index_to_letter(index=end_column_index)
        except ValueError:
            raise ValueError(
                f"Column '{end_column_name}' not found in sheet headers: {headers}"
            )

        # 2. Read data from A to the found end column
        range_name = f"Input!A:{end_column_letter}"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
            .execute()
        )
        values = result.get("values", [])
        df: pd.DataFrame | None = pd.DataFrame(
            data=values[1:],
            columns=values[0],
        )
        if df is not None:
            return df
        else:
            raise ValueError("No system dataframe found")
    except Exception as e:
        logging.warning(f"An error occurred: {e}")
        raise ValueError("Something went wrong when reading the google sheet")


if __name__ == "__main__":
    # The ID of your Google Sheet (found in the URL)
    SPREADSHEET_ID = "1XEQfggOTW8xIqK_fhBOHi5zFNK2YRmy7mr1IfeVE8vA"

    # Execute
    read_google_sheet(
        spreadsheet_id=SPREADSHEET_ID,
    )
