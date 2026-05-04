import json
import os
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
import requests
import xarray as xr
from core.crud.operational.qse_integrations import (
    get_qse_integration_by_project_id,
)
from core.enumerations import OutputType, ProjectID
from core.utils.pandas_datetime import index_to_numpy_ns
from dotenv import load_dotenv
from kpi.base.enumeration import TimeCoord
from kpi.base.exception import MissingDataError
from numpy.typing import NDArray

load_dotenv()

GENERATOR_URL = (
    "https://api.ptp.energy/ptp/ERCOTNodal/Generator-Settlement-Data/query-columnar"
)
VIRTUAL_URL = (
    "https://api.ptp.energy/ptp/ERCOTNodal/Virtual-Settlement-Data/query-columnar"
)


def get_tps_element_identifier_sync(*, project_id: UUID) -> str:
    qse_integration_query = get_qse_integration_by_project_id(
        project_id=project_id,
    )
    qse_integration = qse_integration_query.get(
        output_type=OutputType.SQLALCHEMY,
    )
    if qse_integration is None:
        raise KeyError("QSE integration not found")
    if qse_integration.qse_project_identifier is None:
        raise KeyError("QSE project identifier not configured")
    return qse_integration.qse_project_identifier


def fetch_tenaska_token() -> str:
    """Fetch a Tenaska/PTP bearer token from env-configured credentials."""
    client_id = os.environ["TENASKA_CLIENT_ID"]
    client_secret = os.environ["TENASKA_CLIENT_SECRET"]
    token_url = os.environ["TENASKA_TOKEN_URL"]
    response = requests.get(
        token_url,
        headers={
            "Accept": "application/json",
        },
        auth=(client_id, client_secret),
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload["data"])


def download_tenaska_data(
    *,
    project_id: UUID,
    start_tz_aware: pd.Timestamp,
    end_tz_aware: pd.Timestamp,
    url: str,
) -> dict[str, Any]:
    """Download raw Tenaska/PTP generator settlement data.

    Args:
        project_id: Project ID used to find PROJECT_ID in env.
        start: Start timestamp for the query.
        end: End timestamp for the query.
    """
    token = fetch_tenaska_token()
    parent_element_identifier = get_tps_element_identifier_sync(project_id=project_id)
    params = {
        "begin": start_tz_aware.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S"),
        "end": end_tz_aware.tz_convert("UTC").strftime("%Y-%m-%d %H:%M:%S"),
        "elementQueryMode": "byParentAndFilter",
        "elementIdentifiers": [parent_element_identifier],
    }
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["data"]


def time_array_from_data(*, data: dict[str, Any]) -> NDArray[np.datetime64]:
    time = pd.DatetimeIndex(data["IntervalStartUtc"], tz="UTC")
    return index_to_numpy_ns(index=time)


def data_array_from_elements(
    *, elements: list[dict[str, Any]], column_name: str, time: NDArray[np.datetime64]
) -> xr.DataArray:
    data_arrays = []
    for element in elements:
        data_points = element["DataPoints"]
        if column_name in data_points:
            value = xr.DataArray(
                np.array(data_points[column_name], dtype="float64"),
                dims=[TimeCoord.TIME_15MIN_UTC.value],
                coords={TimeCoord.TIME_15MIN_UTC.value: time},
            )
            data_arrays.append(value)
    if len(data_arrays) == 0:
        raise MissingDataError(f"No data found for {column_name}")
    concat = xr.concat(data_arrays, dim="temp")
    summed = concat.sum(dim="temp", skipna=True, min_count=1)
    return summed


if __name__ == "__main__":
    data = download_tenaska_data(
        project_id=ProjectID.BEXAR.value,
        start_tz_aware=pd.Timestamp("2026-04-25", tz="America/Chicago"),
        end_tz_aware=pd.Timestamp("2026-04-29", tz="America/Chicago"),
        url=VIRTUAL_URL,
    )
    with open("_data/tenaska_virtual_data.json", "w") as f:
        json.dump(data, f, indent=2)
