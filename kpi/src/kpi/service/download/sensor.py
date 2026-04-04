import pandas as pd
import xarray as xr
from core.enumerations import DeviceType, SensorType
from kpi.base.enumeration import Attrs
from kpi.base.protocol import SensorProtocol
from kpi.domain.util import scale_offset
from kpi.infra.download.sensor import (
    get_existing_columns_df,
    get_sensor_types_map,
    get_tag_polars,
    sensor_data_df,
    tag_df_from_tags_polars,
)
from kpi.infra.pandas_to_xarray import dataframe_to_xarray
from kpi.service.field import Field, NoInputs
from kpi.service.field_registry import FieldRegistry
from kpi.service.observer import observe
from kpi.service.time import end_tz_aware, start_tz_aware
from kpi.service.util import assign_var
from pydantic import BaseModel


class SensorModel(BaseModel, NoInputs):
    sensor_type: SensorType
    project_level: bool
    scale: float | None
    offset: float | None

    def run(
        self,
        *,
        tag_df: pd.DataFrame,
        data_raw: pd.DataFrame,
        sensor_to_device_map: dict[int, int],
    ) -> xr.DataArray | None:
        filtered_df = get_existing_columns_df(tag_df, data_raw, self.sensor_type)

        filtered = filtered_df.rename(columns=tag_df.device_id.to_dict())
        value = dataframe_to_xarray(
            filtered,
            project_level=self.project_level,
            device_type=DeviceType(sensor_to_device_map[self.sensor_type.value]),
        )
        return scale_offset(value, scale=self.scale, offset=self.offset)


def sensor_field(
    sensor_type: SensorType,
    project_level: bool = False,
    scale: float | None = None,
    offset: float | None = None,
) -> Field[SensorModel]:
    return Field[SensorModel](
        SensorModel(
            sensor_type=sensor_type,
            project_level=project_level,
            scale=scale,
            offset=offset,
        )
    )


class SensorSchema(FieldRegistry[SensorProtocol]):
    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        project_name_short = dataset.attrs[Attrs.PROJECT_NAME_SHORT.value]
        sensor_type_id_list = [self.get(field).sensor_type.value for field in self.plan]
        tags_polars = get_tag_polars(
            sensor_type_id_list=sensor_type_id_list,
            project_name_short=project_name_short,
        )

        data_raw = sensor_data_df(
            project_name_short=project_name_short,
            start_local=start_tz_aware(dataset),
            end_local=end_tz_aware(dataset),
            tags_polars=tags_polars,
        )

        # Now we have a dataframe with time on the index and tag ids as the columns

        # For each tag, get corresponding sensor type and device id

        tag_df = tag_df_from_tags_polars(tags=tags_polars)

        # For each sensor type, get corresponding device type

        sensor_to_device_map = get_sensor_types_map(sensor_type_id_list)

        for field in self.plan:
            with observe(field_name=field):
                value = self.get(field).run(
                    tag_df=tag_df,
                    data_raw=data_raw,
                    sensor_to_device_map=sensor_to_device_map,
                )
                assign_var(dataset, field, value)
        return dataset


class SensorMax(BaseModel, NoInputs):
    sensor_type: SensorType
    project_level: bool = False

    def run(
        self,
        *,
        tag_df: pd.DataFrame,
        data_raw: pd.DataFrame,
        sensor_to_device_map: dict[int, int],
    ) -> xr.DataArray | None:
        filtered_df = get_existing_columns_df(tag_df, data_raw, self.sensor_type)

        filtered = filtered_df.rename(columns=tag_df.device_id.to_dict())
        # take maximum across all tags with the same device id
        filtered = filtered.T.groupby(level=0).max().T
        value = dataframe_to_xarray(
            filtered,
            project_level=self.project_level,
            device_type=DeviceType(sensor_to_device_map[self.sensor_type.value]),
        )
        return value
