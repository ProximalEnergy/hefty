from core.enumerations import KPITypeEnum
from kpi.op.upload import UploadModel
from kpi.registry.transform.bess.summarize.api import (
    TransformBessSummarize as Summarize,
)

models: list[UploadModel] = [
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_AVAILABILITY,
        version="2.0.1",
        project_var=Summarize.project_pcs_availability_d,
        device_var=Summarize.pcs_availability_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_AVERAGE_C_RATE,
        version="2.0.0",
        project_var=Summarize.project_avg_pcs_c_rate_d,
        device_var=Summarize.pcs_avg_c_rate_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_AVERAGE_C_RATE_WHILE_CHARGING,
        version="2.0.0",
        project_var=Summarize.project_avg_pcs_c_rate_while_charging_d,
        device_var=Summarize.pcs_avg_c_rate_while_charging_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_AVERAGE_C_RATE_WHILE_DISCHARGING,
        version="2.0.0",
        project_var=Summarize.project_avg_pcs_c_rate_while_discharging_d,
        device_var=Summarize.pcs_avg_c_rate_while_discharging_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_HOURS_CHARGING,
        version="2.0.0",
        project_var=Summarize.project_pcs_hours_charging_d,
        device_var=Summarize.pcs_hours_charging_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_HOURS_DISCHARGING,
        version="2.0.0",
        project_var=Summarize.project_pcs_hours_discharging_d,
        device_var=Summarize.pcs_hours_discharging_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_HOURS_IDLING,
        version="2.0.0",
        project_var=Summarize.project_pcs_hours_idling_d,
        device_var=Summarize.pcs_hours_idling_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_ENERGY_CHARGED_DC,
        version="2.0.0",
        project_var=Summarize.project_pcs_energy_charged_dc_kwh_d,
        device_var=Summarize.pcs_energy_charged_dc_kwh_d,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_ENERGY_DISCHARGED_DC,
        version="2.0.0",
        project_var=Summarize.project_pcs_energy_discharged_dc_kwh_d,
        device_var=Summarize.pcs_energy_discharged_dc_kwh_d,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_AVG_REAL_AC_POWER_WHILE_CHARGING,
        version="2.0.0",
        project_var=Summarize.project_avg_pcs_real_ac_power_while_charging_d,
        device_var=Summarize.pcs_avg_real_ac_power_while_charging_d,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_AVG_REAL_AC_POWER_WHILE_DISCHARGING,
        version="2.0.0",
        project_var=Summarize.project_avg_pcs_real_ac_power_while_discharging_d,
        device_var=Summarize.pcs_avg_real_ac_power_while_discharging_d,
        scale=0.001,
    ),
    # BESS_PCS_EFFICIENCY_CHARGING (91) not implemented
    # BESS_PCS_EFFICIENCY_DISCHARGING (92) not implemented
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY,
        version="2.0.0",
        project_var=Summarize.project_pcs_maximum_continuous_discharged_energy_kwh_d,
        device_var=Summarize.pcs_maximum_continuous_discharged_energy_kwh_d,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_STRING_SOC_VARIANCE,
        version="2.0.0",
        project_var=Summarize.project_avg_pcs_string_soc_variance_d,
        device_var=Summarize.pcs_string_soc_variance_d,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.BESS_PCS_STRING_SOC_BALANCE_SCORE,
        version="2.0.0",
        project_var=Summarize.project_avg_pcs_string_soc_balance_score_d,
        device_var=Summarize.pcs_string_soc_balance_score_d,
    ),
]

UPLOAD_BESS_PCS: dict[str, UploadModel] = {
    model.kpi_type.name: model for model in models
}
