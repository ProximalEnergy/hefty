from core.enumerations import DeviceType
from kpi.op.download.expected_energy import (
    ExpectedEnergyModel,
    expected_energy_field,
)
from kpi.op.field_registry import FieldRegistry


class DownloadExpectedEnergy(FieldRegistry[ExpectedEnergyModel]):
    combiner_expected_power_degraded_kw_5m = expected_energy_field(
        expected_metric_id=1,
        device_type=DeviceType.PV_DC_COMBINER,
        scale=0.001,
    )

    combiner_expected_power_degraded_soiled_kw_5m = expected_energy_field(
        expected_metric_id=2,
        device_type=DeviceType.PV_DC_COMBINER,
        scale=0.001,
    )

    project_expected_power_degraded_kw_5m = expected_energy_field(
        expected_metric_id=5,
        device_type=DeviceType.PROJECT,
        project_level=True,
        scale=0.001,
    )

    project_expected_power_degraded_soiled_kw_5m = expected_energy_field(
        expected_metric_id=6,
        device_type=DeviceType.PROJECT,
        project_level=True,
        scale=0.001,
    )

    combiner_expected_power_kw_5m = expected_energy_field(
        expected_metric_id=7,
        device_type=DeviceType.PV_DC_COMBINER,
        scale=0.001,
    )

    combiner_expected_power_soiled_kw_5m = expected_energy_field(
        expected_metric_id=8,
        device_type=DeviceType.PV_DC_COMBINER,
        scale=0.001,
    )

    project_expected_power_kw_5m = expected_energy_field(
        expected_metric_id=11,
        device_type=DeviceType.PROJECT,
        project_level=True,
        scale=0.001,
    )

    project_expected_power_soiled_kw_5m = expected_energy_field(
        expected_metric_id=12,
        device_type=DeviceType.PROJECT,
        project_level=True,
        scale=0.001,
    )
