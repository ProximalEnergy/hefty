import datetime
import json
import os
import uuid
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import numpy as np
import pandas as pd
import psycopg2
import xarray as xr
from core.database import with_db
from core.enumerations import KPITypeEnum
from kpi.base.enumeration import TimeCoord
from kpi.infra.xarray_to_pandas import (
    xarray_device_time_series_to_pandas,
    xarray_time_series_to_pandas,
)
from pydantic import BaseModel, BeforeValidator

from core import models


# 1. Define the reusable coercion function
def to_finite_float(value: Any) -> Any:
    """
    Map NaN, Inf, and non-numeric values to None; leave finite numbers unchanged.
    """
    if np.isfinite(value):
        return value
    return None


# Define a custom type alias for clarity and reuse
FiniteFloat = Annotated[float | None, BeforeValidator(to_finite_float)]


class DeviceDataJson(BaseModel):
    device_values: dict[int, FiniteFloat]

    model_config = {
        "arbitrary_types_allowed": True,  # Allow numpy types
    }


class KPIDataRow(BaseModel):
    """
    Pydantic model for validating and coercing KPI data rows.
    """

    date: datetime.date
    project_id: uuid.UUID
    kpi_type_id: int
    device_data_json: DeviceDataJson | None
    project_data: float
    version: str

    model_config = {
        "arbitrary_types_allowed": True,  # Allow numpy types
    }


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
                    INSERT INTO operational.kpi_data (
                        date, project_id, kpi_type_id,
                        device_data_json, project_data, version
                    )
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
    application_name = f"kpi_{stem}"
    return application_name


def arrays_to_rows(
    *,
    project_data: xr.DataArray,
    device_data: xr.DataArray | None,
    version: str,
    project_id: UUID,
    kpi_type: KPITypeEnum,
    start: datetime.date,
    end: datetime.date,
) -> list[KPIDataRow]:
    data_rows = []
    project_xarray = project_data
    if TimeCoord.DATE_LOCAL.value not in project_xarray.dims:
        raise ValueError(
            "Time.DATE_LOCAL dimension not present in xr.DataArray "
            f"{project_xarray.name}"
        )
    project_series = xarray_time_series_to_pandas(project_xarray)
    project_series.index = project_series.index.date  # type: ignore
    project_map = project_series.to_dict()

    devices_xarray = None

    if device_data is not None:
        devices_xarray = device_data
        if TimeCoord.DATE_LOCAL.value not in devices_xarray.dims:
            raise ValueError(
                "Time.DATE_LOCAL dimension not present in xr.DataArray "
                f"{devices_xarray.name}"
            )
        devices_df = xarray_device_time_series_to_pandas(devices_xarray)
        devices_df.index = devices_df.index.date  # type: ignore

    kpi_dates = pd.date_range(start=start, end=end, freq="D", inclusive="left")

    for date in kpi_dates:
        date_date = date.date()
        row = KPIDataRow(
            date=date_date,
            project_id=project_id,
            kpi_type_id=kpi_type.value,
            device_data_json=None,
            project_data=project_map[date_date],
            version=version,
        )
        if devices_xarray is not None:
            row.device_data_json = DeviceDataJson(
                device_values=devices_df.loc[row.date].to_dict()
            )
        data_rows.append(row)

    return data_rows


def kpi_get_kpi_instances(
    project_id: UUID,
) -> list[int]:
    with with_db(schema=None) as db:
        kpi_instances = db.query(models.KPIInstance).filter(
            models.KPIInstance.project_id == project_id
        )
        kpi_type_ids = [r.kpi_type_id for r in kpi_instances]
    return kpi_type_ids
