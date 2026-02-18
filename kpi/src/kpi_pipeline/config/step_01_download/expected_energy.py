from core.enumerations import DeviceType

from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import ExpectedEnergyModel
from kpi_pipeline.services.schema import DownloadExpectedEnergySchema


class DownloadExpectedEnergy(DownloadExpectedEnergySchema):
    pv_dc_combiner_irradiance_poa_expected_w_m2_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=13,
            device_type=DeviceType.PV_DC_COMBINER,
        )
    )

    pv_dc_combiner_power_expected_degraded_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=1,
            device_type=DeviceType.PV_DC_COMBINER,
            scale=0.001,
        )
    )

    pv_dc_combiner_power_expected_degraded_soiled_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=2,
            device_type=DeviceType.PV_DC_COMBINER,
            scale=0.001,
        )
    )

    pv_pcs_power_expected_degraded_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=3,
            device_type=DeviceType.PV_PCS,
            scale=0.001,
        )
    )

    pv_pcs_power_expected_degraded_soiled_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=4,
            device_type=DeviceType.PV_PCS,
            scale=0.001,
        )
    )

    project_power_expected_degraded_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=5,
            device_type=DeviceType.PROJECT,
            project_level=True,
            scale=0.001,
        )
    )

    project_power_expected_degraded_soiled_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=6,
            device_type=DeviceType.PROJECT,
            project_level=True,
            scale=0.001,
        )
    )

    pv_dc_combiner_power_expected_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=7,
            device_type=DeviceType.PV_DC_COMBINER,
            scale=0.001,
        )
    )

    pv_dc_combiner_power_expected_soiled_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=8,
            device_type=DeviceType.PV_DC_COMBINER,
            scale=0.001,
        )
    )

    pv_pcs_power_expected_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=9,
            device_type=DeviceType.PV_PCS,
            scale=0.001,
        )
    )

    pv_pcs_power_expected_soiled_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=10,
            device_type=DeviceType.PV_PCS,
            scale=0.001,
        )
    )

    project_power_expected_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=11,
            device_type=DeviceType.PROJECT,
            project_level=True,
            scale=0.001,
        )
    )

    project_power_expected_soiled_kw_5m = Field(
        ExpectedEnergyModel(
            expected_metric_id=12,
            device_type=DeviceType.PROJECT,
            project_level=True,
            scale=0.001,
        )
    )
