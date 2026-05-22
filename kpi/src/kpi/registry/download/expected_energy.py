from core.enumerations import DeviceTypeEnum

from kpi.op.download.expected_energy import (
    ExpectedEnergyModel,
)
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry


class DownloadExpectedEnergy(FieldRegistry[ExpectedEnergyModel]):
    combiner_expected_energy_degraded_kwh_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=1,
            device_type=DeviceTypeEnum.PV_DC_COMBINER,
            scale=0.001 / 12,
        )
    )

    combiner_expected_energy_degraded_soiled_kwh_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=2,
            device_type=DeviceTypeEnum.PV_DC_COMBINER,
            scale=0.001 / 12,
        )
    )

    project_expected_energy_degraded_kwh_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=5,
            device_type=DeviceTypeEnum.PROJECT,
            project_level=True,
            scale=0.001 / 12,
        )
    )

    project_expected_energy_degraded_soiled_kwh_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=6,
            device_type=DeviceTypeEnum.PROJECT,
            project_level=True,
            scale=0.001 / 12,
        )
    )

    combiner_expected_energy_kwh_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=7,
            device_type=DeviceTypeEnum.PV_DC_COMBINER,
            scale=0.001 / 12,
        )
    )

    combiner_expected_energy_soiled_kwh_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=8,
            device_type=DeviceTypeEnum.PV_DC_COMBINER,
            scale=0.001 / 12,
        )
    )

    project_expected_energy_kwh_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=11,
            device_type=DeviceTypeEnum.PROJECT,
            project_level=True,
            scale=0.001 / 12,
        )
    )

    project_expected_energy_soiled_kwh_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=12,
            device_type=DeviceTypeEnum.PROJECT,
            project_level=True,
            scale=0.001 / 12,
        )
    )
