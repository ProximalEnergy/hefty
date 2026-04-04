import xarray as xr
from core.crud.project.data_expected import get_project_data_expected
from core.db_query import OutputType
from core.enumerations import DeviceType
from kpi.base.enumeration import Attrs
from kpi.base.util import coord
from kpi.domain.util import scale_offset
from kpi.infra.pandas_to_xarray import dataframe_to_xarray
from kpi.service.field import Field, NoInputs
from kpi.service.field_registry import FieldRegistry
from kpi.service.observer import observe
from kpi.service.time import end_tz_aware, start_tz_aware
from kpi.service.util import assign_var
from pydantic import BaseModel

from core import models


class ExpectedEnergyModel(BaseModel, NoInputs):
    expected_metric_id: int
    device_type: DeviceType
    project_level: bool
    scale: float | None
    offset: float | None


def field(
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


class DownloadExpectedEnergy(FieldRegistry[ExpectedEnergyModel]):
    combiner_expected_poa_irradiance_w_m2_5m = field(
        expected_metric_id=13,
        device_type=DeviceType.PV_DC_COMBINER,
    )

    combiner_expected_power_degraded_kw_5m = field(
        expected_metric_id=1,
        device_type=DeviceType.PV_DC_COMBINER,
        scale=0.001,
    )

    combiner_expected_power_degraded_soiled_kw_5m = field(
        expected_metric_id=2,
        device_type=DeviceType.PV_DC_COMBINER,
        scale=0.001,
    )

    inverter_expected_power_degraded_kw_5m = field(
        expected_metric_id=3,
        device_type=DeviceType.PV_INVERTER,
        scale=0.001,
    )

    inverter_expected_power_degraded_soiled_kw_5m = field(
        expected_metric_id=4,
        device_type=DeviceType.PV_INVERTER,
        scale=0.001,
    )

    project_expected_power_degraded_kw_5m = field(
        expected_metric_id=5,
        device_type=DeviceType.PROJECT,
        project_level=True,
        scale=0.001,
    )

    project_expected_power_degraded_soiled_kw_5m = field(
        expected_metric_id=6,
        device_type=DeviceType.PROJECT,
        project_level=True,
        scale=0.001,
    )

    combiner_expected_power_kw_5m = field(
        expected_metric_id=7,
        device_type=DeviceType.PV_DC_COMBINER,
        scale=0.001,
    )

    combiner_expected_power_soiled_kw_5m = field(
        expected_metric_id=8,
        device_type=DeviceType.PV_DC_COMBINER,
        scale=0.001,
    )

    inverter_expected_power_kw_5m = field(
        expected_metric_id=9,
        device_type=DeviceType.PV_INVERTER,
        scale=0.001,
    )

    inverter_expected_power_soiled_kw_5m = field(
        expected_metric_id=10,
        device_type=DeviceType.PV_INVERTER,
        scale=0.001,
    )

    project_expected_power_kw_5m = field(
        expected_metric_id=11,
        device_type=DeviceType.PROJECT,
        project_level=True,
        scale=0.001,
    )

    project_expected_power_soiled_kw_5m = field(
        expected_metric_id=12,
        device_type=DeviceType.PROJECT,
        project_level=True,
        scale=0.001,
    )

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
