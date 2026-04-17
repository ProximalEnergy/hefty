import xarray as xr
from core.crud.project.data_expected import get_project_data_expected
from core.db_query import OutputType
from core.enumerations import DeviceType
from kpi.base.enumeration import Attrs
from kpi.base.util import coord
from kpi.domain.util import scale_offset
from kpi.infra.pandas_to_xarray import dataframe_to_xarray
from kpi.op.field import Field, NoInputs
from kpi.op.field_registry import FieldRegistry
from kpi.op.observer import observe
from kpi.op.time import end_tz_aware, start_tz_aware
from kpi.op.util import assign_var
from pydantic import BaseModel

from core import models


class ExpectedEnergyModel(BaseModel, NoInputs):
    expected_metric_id: int
    device_type: DeviceType
    project_level: bool
    scale: float | None
    offset: float | None


def expected_energy_field(
    expected_metric_id: int,
    device_type: DeviceType,
    project_level: bool = False,
    scale: float | None = None,
    offset: float | None = None,
) -> Field[ExpectedEnergyModel]:
    return Field[ExpectedEnergyModel](
        ExpectedEnergyModel(
            expected_metric_id=expected_metric_id,
            device_type=device_type,
            project_level=project_level,
            scale=scale,
            offset=offset,
        )
    )


class ExpectedEnergySchema(FieldRegistry[ExpectedEnergyModel]):
    def run(self, dataset: xr.Dataset) -> xr.Dataset:
        expected_metric_ids = [
            self.get(field).expected_metric_id for field in self.plan
        ]
        device_types = set(self.get(field).device_type for field in self.plan)
        all_device_ids: list[int] = []
        for device_type in device_types:
            all_device_ids.extend(dataset.coords[coord(device_type)])
        model_list = get_project_data_expected(
            expected_metric_ids=expected_metric_ids,
            device_ids=all_device_ids,
            start=start_tz_aware(dataset),
            end=end_tz_aware(dataset),
        ).get(
            output_type=OutputType.PANDAS,
            schema=dataset.attrs[Attrs.PROJECT_NAME_SHORT.value],
        )

        expected_df = model_list.set_index(models.DataExpected.time.name)

        for field in self.plan:
            with observe(field_name=field):
                model = self.get(field)
                filtered_df = expected_df.loc[
                    expected_df.expected_metric_id == model.expected_metric_id
                ]
                filtered = filtered_df.pivot_table(
                    index=models.DataExpected.time.name,
                    columns=models.DataExpected.device_id.name,
                    values=models.DataExpected.value.name,
                )
                value = dataframe_to_xarray(
                    filtered,
                    project_level=model.project_level,
                    device_type=model.device_type,
                    skip_if_project_level_empty=True,
                )
                if value is None:
                    continue
                assign_var(
                    dataset,
                    field,
                    scale_offset(value, scale=model.scale, offset=model.offset),
                )
        return dataset
