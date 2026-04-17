import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import Attrs
from kpi.infra.download.events import download_events_df
from kpi.infra.pandas_to_xarray import dataframe_to_xarray
from kpi.op.field import Field, NoInputs
from kpi.op.field_registry import FieldRegistry
from kpi.op.observer import observe
from kpi.op.time import end_tz_aware, start_tz_aware
from pydantic import BaseModel


class EventsModel(BaseModel, NoInputs):
    device_type: DeviceType
    project_level: bool


def event_model_field(
    device_type: DeviceType,
    project_level: bool = False,
) -> Field[EventsModel]:
    return Field[EventsModel](
        EventsModel(
            device_type=device_type,
            project_level=project_level,
        )
    )


class EventSchema(FieldRegistry[EventsModel]):
    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        project_name_short = dataset.attrs[Attrs.PROJECT_NAME_SHORT.value]

        device_type_ids = [self.get(field).device_type.value for field in self.plan]
        df_events = download_events_df(
            project_name_short=project_name_short,
            start_tz_aware=start_tz_aware(dataset),
            end_tz_aware=end_tz_aware(dataset),
            device_type_ids=device_type_ids,
        )

        for field in self.plan:
            with observe(field_name=field):
                model = self.get(field)
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
                dataset[field] = value

        return dataset
