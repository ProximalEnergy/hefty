import datetime

import pandas as pd
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import Attrs, TimeCoords
from kpi.base.util import coord
from kpi.infra.download.devices import download_device_df
from kpi.infra.util import get_project_from_database
from pydantic import validate_call

from core import models

device_types = [
    DeviceType.PROJECT,
    DeviceType.PV_BLOCK,
    DeviceType.PV_DC_COMBINER,
    DeviceType.PV_INVERTER,
    DeviceType.MET_STATION,
    DeviceType.TRACKER_ROW,
    DeviceType.PV_INVERTER_MODULE,
    DeviceType.BESS_MV_CIRCUIT_METER,
    DeviceType.BESS_PCS,
    DeviceType.BESS_PCS_MODULE,
    DeviceType.BESS_PCS_MODULE_GROUP,
    DeviceType.BESS_BANK,
    DeviceType.BESS_STRING,
]


@validate_call
def create_dataset(
    project_name_short: str,
    start_date: datetime.date,
    end_date: datetime.date,
) -> xr.Dataset:
    # Time coordinates
    project = get_project_from_database(project_name_short)

    time_5min_local = pd.date_range(
        start=start_date,
        end=end_date,
        freq="5min",
        inclusive="both",
        tz=project.time_zone,
    )

    time_5min_utc = time_5min_local.tz_convert("UTC").tz_localize(None)

    date_local = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D",
        inclusive="both",
    )

    time_coords = {
        TimeCoords.TIME_5MIN_UTC: time_5min_utc.values,
        TimeCoords.DATE_LOCAL: date_local.values,
    }

    # Device coordinates
    devices_df = download_device_df(
        project_name_short,
        [device_type.value for device_type in device_types],
    )

    device_coords = {}

    for device_type in device_types:
        device_coords[coord(device_type)] = devices_df[
            devices_df[models.Device.device_type_id.name] == device_type.value
        ].index.values

    # Attributes
    attrs = {
        Attrs.PROJECT_NAME_SHORT: project_name_short,
        Attrs.START_DATE: start_date.strftime("%Y-%m-%d"),
        Attrs.END_DATE: end_date.strftime("%Y-%m-%d"),
        Attrs.TIME_ZONE: project.time_zone,
    }

    return xr.Dataset(
        data_vars={},
        coords=time_coords | device_coords,
        attrs=attrs,
    )
