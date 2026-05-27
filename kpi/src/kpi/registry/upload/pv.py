from core.enumerations import KPITypeEnum

from kpi.op.upload import UploadModel
from kpi.registry.transform.pv.summarize import TransformPvSummarize as Summarize

models: list[UploadModel] = [
    # =======================================================
    # Project KPIs
    # =======================================================
    UploadModel(
        kpi_type=KPITypeEnum.PROJECT_ENERGY_PRODUCTION,
        version="2.0.0",
        project_var=Summarize.project_energy_production_kwh_d.name,
        scale=0.001,
    ),
    # SMA_INVERTER_AVAILABILITY_UPTIME_PROJECT (23) deprecated
    UploadModel(
        kpi_type=KPITypeEnum.SPECIFIC_YIELD,
        version="2.0.0",
        project_var=Summarize.specific_yield_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PERFORMANCE_RATIO,
        version="2.0.0",
        project_var=Summarize.performance_ratio_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PV_PROJECT_SOLV_CONTRACTUAL_AVAILABILITY,
        version="2.0.0",
        project_var=Summarize.project_solv_contractual_availability_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PV_PROJECT_SOLV_PERIOD_MWH_PRODUCED,
        version="2.0.0",
        project_var=Summarize.project_solv_period_produced_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PV_PROJECT_SOLV_PERIOD_MWH_LOST,
        version="2.0.0",
        project_var=Summarize.project_solv_period_lost_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PV_PROJECT_PERFORMANCE_INDEX,
        version="2.0.0",
        project_var=Summarize.project_performance_index_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PV_PROJECT_EXPECTED_ENERGY_DELIVERED,
        version="2.0.0",
        project_var=Summarize.project_expected_energy_delivered_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PV_PROJECT_CURTAILMENT,
        version="2.0.0",
        project_var=Summarize.project_curtailed_energy_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PV_PROJECT_INVERTER_MODULE_TO_METER_EFFICIENCY,
        version="2.0.1",
        project_var=Summarize.project_inverter_module_to_meter_efficiency_d.name,
    ),
    # =======================================================
    # PV Inverter KPIs
    # =======================================================
    UploadModel(
        kpi_type=KPITypeEnum.PV_INVERTER_MECHANICAL_AVAILABILITY,
        version="2.0.0",
        project_var=Summarize.project_inverter_mechanical_availability_d.name,
        device_var=Summarize.inverter_mechanical_availability_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PV_INVERTER_ENERGY_PRODUCTION,
        version="2.0.0",
        project_var=Summarize.project_pcs_energy_production_kwh_d.name,
        device_var=Summarize.inverter_energy_production_kwh_d.name,
        scale=0.001,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PROJECT_PV_INVERTER_MECHANICAL_AVAILABILITY,
        version="2.0.0",
        project_var=Summarize.project_inverter_mechanical_availability_d.name,
        device_var=Summarize.inverter_mechanical_availability_d.name,
    ),
    # =======================================================
    # PV Inverter Module KPIs
    # =======================================================
    UploadModel(
        kpi_type=KPITypeEnum.PV_INVERTER_MODULE_ENERGY_PRODUCTION,
        version="2.0.0",
        project_var=Summarize.project_inverter_module_energy_kwh_d.name,
        device_var=Summarize.inverter_module_energy_kwh_d.name,
        scale=0.001,
    ),
    # =======================================================
    # PV DC Combiner KPIs
    # =======================================================
    UploadModel(
        kpi_type=KPITypeEnum.PV_DC_COMBINER_FIELD_HEALTH,
        version="2.0.0",
        project_var=Summarize.project_avg_combiner_field_health_d.name,
        device_var=Summarize.combiner_field_health_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.MODULE_STATE_OF_HEALTH_BY_COMBINER,
        version="2.0.0",
        project_var=Summarize.project_combiner_module_excess_degradation_d.name,
        device_var=Summarize.combiner_module_excess_degradation_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.PV_DC_COMBINER_MECHANICAL_AVAILABILITY,
        version="2.0.0",
        project_var=Summarize.project_combiner_mechanical_availability_d.name,
        device_var=Summarize.combiner_mechanical_availability_d.name,
    ),
    # =======================================================
    # Tracker Row KPIs
    # =======================================================
    UploadModel(
        kpi_type=KPITypeEnum.TRACKER_AVAILABILITY_BY_ROW,
        version="2.0.0",
        project_var=Summarize.project_tracker_row_availability_d.name,
        device_var=Summarize.tracker_row_availability_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_ROW,
        version="2.0.0",
        project_var=Summarize.project_tracker_row_deviation_from_setpoint_deg_d.name,
        device_var=Summarize.tracker_row_deviation_from_setpoint_deg_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_ROW,
        version="2.0.0",
        project_var=Summarize.project_tracker_row_setpoint_deviating_from_median_deg_d.name,
        device_var=Summarize.tracker_row_setpoint_deviating_from_median_deg_d.name,
    ),
    # =======================================================
    # PV Block KPIs
    # =======================================================
    UploadModel(
        kpi_type=KPITypeEnum.TRACKER_AVAILABILITY_BY_BLOCK,
        version="2.0.0",
        project_var=Summarize.project_tracker_row_availability_d.name,
        device_var=Summarize.block_tracker_row_availability_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.TRACKER_POSITION_DEVIATING_FROM_SETPOINT_BY_BLOCK,
        version="2.0.0",
        project_var=Summarize.project_tracker_row_deviation_from_setpoint_deg_d.name,
        device_var=Summarize.block_tracker_row_deviation_from_setpoint_deg_d.name,
    ),
    UploadModel(
        kpi_type=KPITypeEnum.TRACKER_SETPOINT_DEVIATING_FROM_MEDIAN_BY_BLOCK,
        version="2.0.0",
        project_var=Summarize.project_tracker_row_setpoint_deviating_from_median_deg_d.name,
        device_var=Summarize.block_tracker_row_setpoint_deviating_from_median_deg_d.name,
    ),
]
UPLOAD_PV = {model.kpi_type.name: model for model in models}
