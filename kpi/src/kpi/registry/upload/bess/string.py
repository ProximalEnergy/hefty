from core.enumerations import KPIType
from kpi.op.upload import UploadModel, UploadSchema
from kpi.registry.transform.bess.summarize.api import TransformBessSummarize

T = TransformBessSummarize

models: list[UploadModel] = [
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVERAGE_SOC_PERCENT,
        version="2.0.0",
        project_var=T.project_avg_string_soc_d.name,
        device_var=T.string_avg_soc_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_RESTING_SOC_PERCENT,
        version="2.0.0",
        project_var=T.project_avg_string_resting_soc_d.name,
        device_var=T.string_avg_resting_soc_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_CYCLE_COUNT,
        version="2.0.0",
        project_var=T.project_avg_string_cycle_count_d.name,
        device_var=T.string_cycle_count_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_ENERGY_CHARGED,
        version="2.0.0",
        project_var=T.project_string_energy_charged_kwh_d.name,
        device_var=T.string_energy_charged_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_ENERGY_DISCHARGED,
        version="2.0.0",
        project_var=T.project_string_energy_discharged_kwh_d.name,
        device_var=T.string_energy_discharged_kwh_d.name,
        scale=0.001,
    ),
    # BESS_STRING_RTE (45) not implemented
    UploadModel(
        kpi_type=KPIType.BESS_STRING_DEPTH_OF_DISCHARGE,
        version="2.0.0",
        project_var=T.project_avg_string_dod_d.name,
        device_var=T.string_avg_dod_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_SOH,
        version="2.0.0",
        project_var=T.project_string_soh_d.name,
        device_var=T.string_soh_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVERAGE_C_RATE,
        version="2.0.0",
        project_var=T.project_avg_string_c_rate_d.name,
        device_var=T.string_avg_c_rate_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_MIN_MODULE_TEMP,
        version="2.0.0",
        project_var=T.project_string_min_module_temp_d.name,
        device_var=T.string_min_module_temp_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_MAX_MODULE_TEMP,
        version="2.0.0",
        project_var=T.project_string_max_module_temp_d.name,
        device_var=T.string_max_module_temp_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVG_MODULE_TEMP,
        version="2.0.0",
        project_var=T.project_string_avg_module_temp_d.name,
        device_var=T.string_avg_module_temp_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVG_C_RATE_WHILE_CHARGING,
        version="2.0.0",
        project_var=T.project_avg_string_c_rate_while_charging_d.name,
        device_var=T.string_avg_c_rate_while_charging_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVG_C_RATE_WHILE_DISCHARGING,
        version="2.0.0",
        project_var=T.project_avg_string_c_rate_while_discharging_d.name,
        device_var=T.string_avg_c_rate_while_discharging_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_MIN_CELL_VOLTAGE,
        version="2.0.0",
        project_var=T.project_min_cell_voltage_d.name,
        device_var=T.string_min_cell_voltage_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVG_CELL_VOLTAGE,
        version="2.0.0",
        project_var=T.project_avg_cell_voltage_d.name,
        device_var=T.string_avg_cell_voltage_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_MAX_CELL_VOLTAGE,
        version="2.0.0",
        project_var=T.project_max_cell_voltage_d.name,
        device_var=T.string_max_cell_voltage_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVG_CURRENT,
        version="2.0.0",
        project_var=T.project_avg_string_current_amps_d.name,
        device_var=T.string_avg_current_amps_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_MAX_CURRENT,
        version="2.0.0",
        project_var=T.project_max_string_current_amps_d.name,
        device_var=T.string_max_current_amps_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_MIN_CURRENT,
        version="2.0.0",
        project_var=T.project_min_string_current_amps_d.name,
        device_var=T.string_min_current_amps_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVG_CURRENT_WHILE_CHARGING,
        version="2.0.0",
        project_var=T.project_avg_string_current_while_charging_amps_d.name,
        device_var=T.string_avg_current_while_charging_amps_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVG_CURRENT_WHILE_DISCHARGING,
        version="2.0.0",
        project_var=T.project_avg_string_current_while_discharging_amps_d.name,
        device_var=T.string_avg_current_while_discharging_amps_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_AVG_CELL_TEMPERATURE,
        version="2.0.0",
        project_var=T.project_string_avg_cell_temperature_d.name,
        device_var=T.string_avg_cell_temperature_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_MAX_CELL_TEMPERATURE,
        version="2.0.0",
        project_var=T.project_max_cell_temperature_d.name,
        device_var=T.string_max_cell_temperature_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_MIN_CELL_TEMPERATURE,
        version="2.0.0",
        project_var=T.project_min_cell_temperature_d.name,
        device_var=T.string_min_cell_temperature_d.name,
    ),
    UploadModel(
        kpi_type=KPIType.BESS_STRING_DEGRADATION,
        version="2.0.0",
        project_var=T.project_string_degradation_d.name,
        device_var=T.string_degradation_d.name,
    ),
    # BESS_STRING_AVAILABILITY (96) not implemented
    # BESS_STRING_MAXIMUM_CONTINUOUS_DISCHARGED_ENERGY (108) not implemented
]

registry = {model.kpi_type.name: model for model in models}


class UploadBessString(UploadSchema):
    """Registry of BESS string KPI fields for upload."""

    _field_registry = registry
