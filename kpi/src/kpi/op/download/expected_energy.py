import xarray as xr
from core.crud.project.data_expected import get_project_data_expected
from core.db_query import OutputType
from core.enumerations import DeviceTypeEnum
from kpi.base.util import coord
from kpi.domain.util import scale_offset
from kpi.infra.pandas_to_xarray import dataframe_to_xarray
from kpi.op.context import get_context
from kpi.op.field import NoInputs
from kpi.op.observer import observe
from kpi.op.plan import MultiFieldPlan
from kpi.op.schema import SchemaAbstract
from kpi.op.util import assign_var
from pydantic import BaseModel

from core import models


class ExpectedEnergyModel(BaseModel, NoInputs):
    expected_metric_id: int
    device_type: DeviceTypeEnum
    project_level: bool = False
    scale: float | None = None
    offset: float | None = None


class ExpectedEnergySchema(SchemaAbstract[ExpectedEnergyModel]):
    def run(self, dataset: xr.Dataset, plan: MultiFieldPlan) -> xr.Dataset:
        context = get_context(dataset)
        field_names = plan.outputs()
        expected_metric_ids = [
            self.map[field_name].expected_metric_id for field_name in field_names
        ]
        device_types = set(
            self.map[field_name].device_type for field_name in field_names
        )
        all_device_ids: list[int] = []
        for device_type in device_types:
            all_device_ids.extend(dataset.coords[coord(device_type)])
        model_list = get_project_data_expected(
            expected_metric_ids=expected_metric_ids,
            device_ids=all_device_ids,
            start=context.start_tz_aware,
            end=context.end_tz_aware,
        ).get(
            output_type=OutputType.PANDAS,
            schema=context.project_name_short,
        )

        expected_df = model_list.set_index(models.DataExpected.time.name)

        for field_name in field_names:
            with observe(field_name=field_name):
                model = self.map[field_name]
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
                )
                assign_var(
                    dataset,
                    field_name,
                    scale_offset(value, scale=model.scale, offset=model.offset),
                )
        return dataset
