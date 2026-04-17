from core.enumerations import KPIType
from kpi.op.upload import UploadModel, UploadSchema
from kpi.registry.transform.bess.summarize.api import TransformBessSummarize

T = TransformBessSummarize

models: list[UploadModel] = [
    UploadModel(
        kpi_type=KPIType.BESS_PCS_AVAILABILITY,
        version="2.0.1",
        project_var=T.project_pcs_availability_d.name,
        device_var=T.pcs_availability_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_AVERAGE_C_RATE,
        version="2.0.0",
        project_var=T.project_avg_pcs_c_rate_d.name,
        device_var=T.pcs_avg_c_rate_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_AVERAGE_C_RATE_WHILE_CHARGING,
        version="2.0.0",
        project_var=T.project_avg_pcs_c_rate_while_charging_d.name,
        device_var=T.pcs_avg_c_rate_while_charging_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_AVERAGE_C_RATE_WHILE_DISCHARGING,
        version="2.0.0",
        project_var=T.project_avg_pcs_c_rate_while_discharging_d.name,
        device_var=T.pcs_avg_c_rate_while_discharging_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_HOURS_CHARGING,
        version="2.0.0",
        project_var=T.project_pcs_hours_charging_d.name,
        device_var=T.pcs_hours_charging_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_HOURS_DISCHARGING,
        version="2.0.0",
        project_var=T.project_pcs_hours_discharging_d.name,
        device_var=T.pcs_hours_discharging_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_HOURS_IDLING,
        version="2.0.0",
        project_var=T.project_pcs_hours_idling_d.name,
        device_var=T.pcs_hours_idling_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_ENERGY_CHARGED_DC,
        version="2.0.0",
        project_var=T.project_pcs_energy_charged_dc_kwh_d.name,
        device_var=T.pcs_energy_charged_dc_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_ENERGY_DISCHARGED_DC,
        version="2.0.0",
        project_var=T.project_pcs_energy_discharged_dc_kwh_d.name,
        device_var=T.pcs_energy_discharged_dc_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_AVG_REAL_AC_POWER_WHILE_CHARGING,
        version="2.0.0",
        project_var=T.project_avg_pcs_real_ac_power_while_charging_d.name,
        device_var=T.pcs_avg_real_ac_power_while_charging_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_AVG_REAL_AC_POWER_WHILE_DISCHARGING,
        version="2.0.0",
        project_var=T.project_avg_pcs_real_ac_power_while_discharging_d.name,
        device_var=T.pcs_avg_real_ac_power_while_discharging_d.name,
        scale=0.001,
    ),
    # BESS_PCS_EFFICIENCY_CHARGING (91) not implemented
    # BESS_PCS_EFFICIENCY_DISCHARGING (92) not implemented
    UploadModel(
        kpi_type=KPIType.BESS_PCS_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY,
        version="2.0.0",
        project_var=T.project_pcs_maximum_continuous_discharged_energy_kwh_d.name,
        device_var=T.pcs_maximum_continuous_discharged_energy_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_STRING_SOC_VARIANCE,
        version="2.0.0",
        project_var=T.project_avg_pcs_string_soc_variance_d.name,
        device_var=T.pcs_string_soc_variance_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_PCS_STRING_SOC_BALANCE_SCORE,
        version="2.0.0",
        project_var=T.project_avg_pcs_string_soc_balance_score_d.name,
        device_var=T.pcs_string_soc_balance_score_d.name,
    ),
]

registry = {model.kpi_type.name: model for model in models}


class UploadBessPcs(UploadSchema):
    """Registry of BESS PCS KPI fields for upload."""

    _field_registry = registry
