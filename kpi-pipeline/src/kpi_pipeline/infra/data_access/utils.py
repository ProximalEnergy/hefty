import json
import os
from pathlib import Path

import pandas as pd
import psycopg2
import xarray as xr
from core import models
from core.crud.project.devices import get_project_devices
from core.db_query import OutputType

from kpi_pipeline.base.enums import DeviceType
from kpi_pipeline.base.models import DeviceDataJson, KPIDataRow
from kpi_pipeline.base.protocols import ScaleOffsetProtocol


def validate_kpi_device_data_json(device_data_json: dict) -> dict:
    """
    Validate and transform the KPI device data JSON into a DeviceDataObj model.

    Args:
        device_data_json (dict): The device data in JSON format to be validated.

    Returns:
        dict: A dictionary representation of the validated DeviceDataObj model.
    """
    return DeviceDataJson.model_validate(device_data_json).model_dump()


write_to_db = True


def insert_device_kpi_data_bulk(
    *,
    application_name: str,
    data_rows: list[KPIDataRow],
):
    """
    Bulk insert multiple KPI device data rows into the database.

    Args:
        application_name (str): The name of the application making the connection.
        data_rows (list[dict]): List of dictionaries, where each dictionary contains:
            - date: datetime.date or str (YYYY-MM-DD format)
            - project_id: Union[str, uuid.UUID]
            - kpi_type_id: int
            - device_data_json: dict (must conform to DeviceDataObj interface)
            - project_data: Union[int, float]
            - version: Optional[str] = None

    Each row in data_rows will be validated and coerced using Pydantic models.
    """
    if not data_rows:
        return

    # Validate and prepare all rows using Pydantic
    prepared_rows = []
    rows_to_write = []
    for i, row_dict in enumerate(data_rows):
        try:
            # Let Pydantic handle all validation and coercion
            row = KPIDataRow.model_validate(row_dict)
            rows_to_write.append(row.model_dump(mode="json"))
            prepared_rows.append(
                (
                    row.date,
                    row.project_id,
                    row.kpi_type_id,
                    json.dumps(row.device_data_json.model_dump(), allow_nan=False)
                    if row.device_data_json
                    else None,
                    row.project_data,
                    row.version,
                )
            )
        except Exception as e:
            raise ValueError(f"Error validating row {i}: {e}")

    if write_to_db:
        with psycopg2.connect(
            os.getenv("CONNECTION_STRING_POOLER"),
            application_name=application_name,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO operational.kpi_data (date, project_id, kpi_type_id, device_data_json, project_data, version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, project_id, kpi_type_id)
                    DO UPDATE SET
                        device_data_json = EXCLUDED.device_data_json,
                        project_data = EXCLUDED.project_data,
                        version = EXCLUDED.version;
                    """,
                    prepared_rows,
                )

                conn.commit()

    else:
        # sort the rows by kpi_type_id
        rows_to_write.sort(key=lambda x: x["kpi_type_id"])
        with open("_data/data_rows.json", "w") as f:
            json.dump(rows_to_write, f, indent=4)


def get_application_name(
    file_path: str = "",
) -> str:
    """
    Generate an application name based on the script file name.

    Args:
        file_path (str): The path of the script file.

    Returns:
        str: The application name based on the script file name
    """
    path = Path(file_path)
    stem = path.stem
    application_name = f"reimagined_train_{stem}"
    return application_name


def get_devices_df(project_name_short: str) -> pd.DataFrame:
    devices = get_project_devices(
        device_type_ids=[
            DeviceType.PROJECT,
            DeviceType.BESS_STRING,
            DeviceType.BESS_PCS,
        ],
    ).get(schema=project_name_short, output_type=OutputType.PANDAS)

    return devices.set_index(models.Device.device_id.name)


def scale_offset(x: xr.DataArray, model: ScaleOffsetProtocol) -> xr.DataArray:
    if model.scale is not None:
        x = x * model.scale
    if model.offset is not None:
        x = x + model.offset
    return x
