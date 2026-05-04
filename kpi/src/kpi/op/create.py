import datetime
from uuid import UUID

import pandas as pd
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.context import ContextModel
from kpi.base.enumeration import TIME_DESCRIPTOR, TimeCoord
from kpi.base.util import coord
from kpi.infra.download.devices import download_device_df
from kpi.infra.util import get_project_by_id
from pydantic import validate_call

from core import models

device_types = [
    DeviceTypeEnum.PROJECT,
    DeviceTypeEnum.PV_BLOCK,
    DeviceTypeEnum.PV_DC_COMBINER,
    DeviceTypeEnum.PV_INVERTER,
    DeviceTypeEnum.MET_STATION,
    DeviceTypeEnum.TRACKER_ROW,
    DeviceTypeEnum.PV_INVERTER_MODULE,
    DeviceTypeEnum.BESS_MV_COLLECTOR_CIRCUIT_METER,
    DeviceTypeEnum.BESS_PCS,
    DeviceTypeEnum.BESS_PCS_MODULE,
    DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
    DeviceTypeEnum.BESS_BANK,
    DeviceTypeEnum.BESS_STRING,
]


@validate_call
def create_dataset(
    project_id: UUID,
    start_date: datetime.date,
    end_date: datetime.date,
) -> xr.Dataset:
    # Time coordinates
    project = get_project_by_id(project_id=project_id)

    time_coords = {}

    for time_coord in TimeCoord:
        desc = TIME_DESCRIPTOR[time_coord]
        date_range = pd.date_range(
            start=start_date,
            end=end_date,
            freq=desc.pandas_freq,
            inclusive="both",
            tz=project.time_zone,
        )
        if desc.utc:
            date_range = date_range.tz_convert("UTC")
        date_range = date_range.tz_localize(None)

        time_coords[time_coord.value] = date_range.values

    # Device coordinates
    devices_df = download_device_df(
        project.name_short,
        [device_type.value for device_type in device_types],
    )

    device_coords = {}

    for device_type in device_types:
        device_coords[coord(device_type)] = devices_df[
            devices_df[models.Device.device_type_id.name] == device_type.value
        ].index.values

    context_model = ContextModel(
        project_id=project_id,
        project_name_short=project.name_short,
        start_date=start_date,
        end_date=end_date,
        time_zone=project.time_zone,
    )

    return xr.Dataset(
        data_vars={},
        coords=time_coords | device_coords,
        attrs=context_model.model_dump(mode="json"),
    )
