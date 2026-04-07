import xarray as xr
from core.enumerations import DeviceType, SensorType
from kpi.base.enumeration import Attrs
from kpi.infra.download.sensor import get_existing_columns_df
from kpi.infra.download.status import download_status_df, get_tag_df
from kpi.infra.pandas_to_xarray import pandas_device_time_series_to_xarray
from kpi.service.field import Field, NoInputs
from kpi.service.field_registry import FieldRegistry
from kpi.service.observer import observe
from kpi.service.time import end_tz_aware, start_tz_aware
from kpi.service.util import assign_var
from pydantic import BaseModel


class StatusModel(BaseModel, NoInputs):
    sensor_type: SensorType
    device_type: DeviceType
    failure_modes: list[int]


def status_field(
    sensor_type: SensorType,
    device_type: DeviceType,
    failure_modes: list[int],
) -> Field[StatusModel]:
    return Field[StatusModel](
        StatusModel(
            sensor_type=sensor_type,
            device_type=device_type,
            failure_modes=failure_modes,
        )
    )


class StatusSchema(FieldRegistry[StatusModel]):
    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        project_name_short = dataset.attrs[Attrs.PROJECT_NAME_SHORT.value]
        sensor_type_ids = [self.get(field).sensor_type.value for field in self.plan]
        df_status = download_status_df(
            project_name_short=project_name_short,
            start_tz_aware=start_tz_aware(dataset),
            end_tz_aware=end_tz_aware(dataset),
            sensor_type_ids=sensor_type_ids,
        )
        tag_df = get_tag_df(sensor_type_ids, project_name_short=project_name_short)
        for field in self.plan:
            with observe(field_name=field):
                model = self.get(field)
                filtered_df = get_existing_columns_df(
                    tag_df, df_status, model.sensor_type
                )

                failure_df = filtered_df.isin(model.failure_modes).astype(bool)

                filtered = (
                    failure_df.T.groupby(tag_df.device_id.to_dict()).any().T
                ).astype(bool)
                value = pandas_device_time_series_to_xarray(
                    filtered,
                    device_type=model.device_type,
                )
                assign_var(
                    dataset,
                    field,
                    value,
                )
        return dataset
