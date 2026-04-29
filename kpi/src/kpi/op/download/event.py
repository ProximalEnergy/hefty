import xarray as xr
from core.enumerations import DeviceType
from kpi.infra.download.events import download_events_df
from kpi.infra.pandas_to_xarray import dataframe_to_xarray
from kpi.op.context import get_context
from kpi.op.field import NoInputs
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from pydantic import BaseModel


class EventsModel(BaseModel, NoInputs):
    device_type: DeviceType
    project_level: bool = False


class EventSchema(SchemaAbstract[EventsModel]):
    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        context = get_context(dataset)
        field_names = plan.outputs()

        device_type_ids = [
            self.map[field_name].device_type.value for field_name in field_names
        ]
        df_events = download_events_df(
            project_name_short=context.project_name_short,
            start_tz_aware=context.start_tz_aware,
            end_tz_aware=context.end_tz_aware,
            device_type_ids=device_type_ids,
        )

        for field_name in field_names:
            with observe(field_name=field_name):
                model = self.map[field_name]
                filtered = df_events.loc[
                    df_events.device_type_id == model.device_type.value
                ]
                start_df = filtered.assign(present=1.0).pivot_table(
                    index="time_start",
                    columns="device_id",
                    values="present",
                    aggfunc="sum",
                )
                end_df = filtered.assign(present=-1.0).pivot_table(
                    index="time_end",
                    columns="device_id",
                    values="present",
                    aggfunc="sum",
                )
                filtered = start_df.add(end_df, fill_value=0)
                value = dataframe_to_xarray(
                    filtered,
                    project_level=model.project_level,
                    device_type=model.device_type,
                )
                # allow empty data arrays
                dataset[field_name] = value

        return dataset
