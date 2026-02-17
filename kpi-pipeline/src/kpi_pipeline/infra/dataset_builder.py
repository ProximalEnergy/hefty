from datetime import date

import pandas as pd
import xarray as xr
from pydantic import validate_call

from kpi_pipeline.base.enums import Time, supported_devices
from kpi_pipeline.base.models import ContextModel
from kpi_pipeline.infra.data_access.read import get_project_from_database
from kpi_pipeline.infra.device_manager import DeviceTree


@validate_call
def create_context(
    *,
    project_name_short: str,
    start_date: date,
    end_date: date,
) -> ContextModel:
    project = get_project_from_database(name_short=project_name_short)
    device_tree = DeviceTree.from_project(project=project)
    return ContextModel(
        project=project,
        start_date=start_date,
        end_date=end_date,
        device_tree=device_tree,
    )


def create_dataset(
    *,
    context: ContextModel,
) -> xr.Dataset:
    dataset = xr.Dataset()
    for axis in supported_devices:
        device_ids = context.device_tree.device_ids(device_type=axis)
        if len(device_ids) > 0:
            dataset.coords[axis.name.lower()] = device_ids
    date_time_index = (
        pd.date_range(
            start=context.start_date,
            end=context.end_date,
            freq="5min",
            inclusive="both",
            tz=context.project.time_zone,
        )
        .tz_convert("UTC")
        .tz_localize(None)
    )
    dataset = dataset.assign_coords({Time.TIME_5MIN_UTC.value: date_time_index})
    return dataset
