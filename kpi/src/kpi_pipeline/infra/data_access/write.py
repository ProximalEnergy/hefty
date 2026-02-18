import datetime
from uuid import UUID

import pandas as pd
import xarray as xr
from core.enumerations import KPIType

from kpi_pipeline.base.enums import Time
from kpi_pipeline.base.models import DeviceDataJson, KPIDataRow, KPIMetadata
from kpi_pipeline.infra.data_access.utils import scale_offset
from kpi_pipeline.infra.data_access.xarray_to_pandas import (
    xarray_device_time_series_to_pandas,
    xarray_time_series_to_pandas,
)
from kpi_pipeline.infra.utils import select


def arrays_to_rows(
    dataset: xr.Dataset,
    project_id: UUID,
    kpi_type: KPIType,
    kpi_metadata: KPIMetadata,
    start: datetime.date,
    end: datetime.date,
) -> list[KPIDataRow]:
    data_rows = []
    project_xarray = scale_offset(
        select(dataset, kpi_metadata.project_var), kpi_metadata
    )
    if Time.DATE_LOCAL.value not in project_xarray.dims:
        raise ValueError(
            f"Time.DATE_LOCAL dimension not present in xr.DataArray {project_xarray.name}"
        )
    project_series = xarray_time_series_to_pandas(project_xarray)
    project_series.index = project_series.index.date  # type: ignore
    project_map = project_series.to_dict()

    devices_xarray = None

    if kpi_metadata.device_var is not None:
        devices_xarray = scale_offset(
            select(dataset, kpi_metadata.device_var), kpi_metadata
        )
        if Time.DATE_LOCAL.value not in devices_xarray.dims:
            raise ValueError(
                f"Time.DATE_LOCAL dimension not present in xr.DataArray {devices_xarray.name}"
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
            version=kpi_metadata.version,
        )
        if devices_xarray is not None:
            row.device_data_json = DeviceDataJson(
                device_values=devices_df.loc[row.date].to_dict()
            )
        data_rows.append(row)

    return data_rows
