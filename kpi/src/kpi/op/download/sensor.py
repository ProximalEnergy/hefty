import pandas as pd
import xarray as xr
from core.enumerations import DeviceTypeEnum, SensorTypeEnum
from kpi.base.context import get_context
from kpi.base.protocol import SensorProtocol, schema_protocol, sensor_protocol
from kpi.domain.util import scale_offset
from kpi.infra.download.sensor import (
    get_existing_columns_df,
    get_sensor_types_map,
    get_tag_polars,
    sensor_data_df,
    tag_df_from_tags_polars,
)
from kpi.infra.pandas_to_xarray import dataframe_to_xarray
from kpi.op.download.util import MarkdownDocModel
from kpi.op.field import Field
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import assign_var


@sensor_protocol
class SensorModel(MarkdownDocModel):
    sensor_type: SensorTypeEnum
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
            device_type=DeviceTypeEnum(sensor_to_device_map[self.sensor_type.value]),
        )
        return scale_offset(value, scale=self.scale, offset=self.offset)


def sensor_field(
    sensor_type: SensorTypeEnum,
    project_level: bool = False,
    scale: float | None = None,
    offset: float | None = None,
) -> Field[SensorProtocol]:
    return Field[SensorProtocol](
        SensorModel(
            sensor_type=sensor_type,
            project_level=project_level,
            scale=scale,
            offset=offset,
        )
    )


@schema_protocol
class SensorSchema(SchemaAbstract[SensorProtocol]):
    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        context = get_context(dataset)
        field_names = plan.outputs()
        sensor_type_id_list = [
            self.map[field_name].sensor_type.value for field_name in field_names
        ]
        tags_polars = get_tag_polars(
            sensor_type_id_list=sensor_type_id_list,
            project_name_short=context.project_name_short,
        )

        data_raw = sensor_data_df(
            project_name_short=context.project_name_short,
            start_local=context.start_tz_aware,
            end_local=context.end_tz_aware,
            tags_polars=tags_polars,
        )

        # Now we have a dataframe with time on the index and tag ids as the columns

        # For each tag, get corresponding sensor type and device id

        tag_df = tag_df_from_tags_polars(tags=tags_polars)

        # For each sensor type, get corresponding device type

        sensor_to_device_map = get_sensor_types_map(sensor_type_id_list)

        for field_name in field_names:
            with observe(field_name=field_name):
                value = self.map[field_name].run(
                    tag_df=tag_df,
                    data_raw=data_raw,
                    sensor_to_device_map=sensor_to_device_map,
                )
                assign_var(dataset, field_name, value)
        return dataset


@sensor_protocol
class SensorMax(MarkdownDocModel):
    sensor_type: SensorTypeEnum
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
            device_type=DeviceTypeEnum(sensor_to_device_map[self.sensor_type.value]),
        )
        return value
