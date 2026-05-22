import xarray as xr
from core.enumerations import DeviceTypeEnum, SensorTypeEnum
from kpi.base.context import get_context
from kpi.base.protocol import node_protocol, schema_protocol
from kpi.infra.download.sensor import get_existing_columns_df
from kpi.infra.download.status import download_status_df, get_tag_df
from kpi.infra.pandas_to_xarray import pandas_device_time_series_to_xarray
from kpi.op.download.util import MarkdownDocModel
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import assign_var


@node_protocol
class StatusModel(MarkdownDocModel):
    sensor_type: SensorTypeEnum
    device_type: DeviceTypeEnum
    failure_modes: list[int]


@schema_protocol
class StatusSchema(SchemaAbstract[StatusModel]):
    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        context = get_context(dataset)
        field_names = plan.outputs()
        sensor_type_ids = [
            self.map[field_name].sensor_type.value for field_name in field_names
        ]
        df_status = download_status_df(
            project_id=context.project_id,
            start_tz_aware=context.start_tz_aware,
            end_tz_aware=context.end_tz_aware,
            sensor_type_ids=sensor_type_ids,
        )
        tag_df = get_tag_df(
            sensor_type_ids,
            project_name_short=context.project_name_short,
        )
        for field_name in field_names:
            with observe(field_name=field_name):
                model = self.map[field_name]
                filtered_df = get_existing_columns_df(
                    tag_df, df_status, model.sensor_type
                )

                failure_df = filtered_df.isin(model.failure_modes).astype(bool)

                filtered = ~(
                    failure_df.T.groupby(tag_df.device_id.to_dict()).any().T
                ).astype(bool)
                value = pandas_device_time_series_to_xarray(
                    filtered,
                    device_type=model.device_type,
                )
                assign_var(
                    dataset,
                    field_name,
                    value,
                )
        return dataset
