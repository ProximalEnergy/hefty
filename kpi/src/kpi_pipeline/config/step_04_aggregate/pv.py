from core.enumerations import DeviceType

from kpi_pipeline.base.enums import Aggregation
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import CoordCombinerModel
from kpi_pipeline.config.helper_fields import (
    _5min_to_daily,
    _aggregate,
    _device_aggregate,
)
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.config.step_03_calculate import Calculate
from kpi_pipeline.services.calc import (
    CalcProcess,
    CombinerMechanicalAvailabilityCalc,
    DcFieldHealthCalc,
    MechanicalAvailabilityCalc,
    PerformanceIndexCalc,
    PerformanceRatioCalc,
    PvDcCombinerModuleExcessDegradationCalc,
    QuotientCalc,
    SolvGuaranteeAvailabilityCalc,
    SolvPeriodKwhLostCalc,
    SolvPeriodKwhProducedCalc,
    TrackerAvailabilityCalc,
    TrackerDeviationFromSetpointCalc,
    TrackerSetpointDeviationFromMedianCalc,
    WeightedAverageCalc,
)
from kpi_pipeline.services.process import FilterToRangeProcess
from kpi_pipeline.services.schema import AddCalculationsSchema


class AggregatePV(AddCalculationsSchema):
    # ============================================================================
    # Tracker Availability Calculations
    # ============================================================================
    # Aggregates tracker availability from 5-minute to daily, measuring how often
    # tracker position matches setpoint within threshold (2.0 degrees)

    block_tracker_availability_d = Field(
        CalcProcess(
            calc=TrackerAvailabilityCalc(
                position_var=Validate.tracker_row_position_deg_5m.var,
                setpoint_var=Validate.tracker_row_setpoint_deg_5m.var,
                time_combiner_model=_5min_to_daily(
                    child_device_axis=DeviceType.TRACKER_ROW,
                    parent_device_axis=DeviceType.PV_BLOCK,
                ),
                threshold_deg=2.0,
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    tracker_row_availability_d = Field(
        CalcProcess(
            calc=TrackerAvailabilityCalc(
                position_var=Validate.tracker_row_position_deg_5m.var,
                setpoint_var=Validate.tracker_row_setpoint_deg_5m.var,
                time_combiner_model=_5min_to_daily(),
                threshold_deg=2.0,
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    project_tracker_availability_d = Field(
        CalcProcess(
            calc=TrackerAvailabilityCalc(
                position_var=Validate.tracker_row_position_deg_5m.var,
                setpoint_var=Validate.tracker_row_setpoint_deg_5m.var,
                time_combiner_model=_5min_to_daily(
                    child_device_axis=DeviceType.TRACKER_ROW,
                ),
                threshold_deg=2.0,
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    # ============================================================================
    # Tracker Deviation Calculations
    # ============================================================================
    # Measures how much tracker position deviates from setpoint or median position

    tracker_row_deviation_from_setpoint_deg_d = Field(
        TrackerDeviationFromSetpointCalc(
            position_var=Validate.tracker_row_position_deg_5m.var,
            setpoint_var=Validate.tracker_row_setpoint_deg_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    block_tracker_deviation_from_setpoint_deg_d = Field(
        TrackerDeviationFromSetpointCalc(
            position_var=Validate.tracker_row_position_deg_5m.var,
            setpoint_var=Validate.tracker_row_setpoint_deg_5m.var,
            time_combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.TRACKER_ROW,
                parent_device_axis=DeviceType.PV_BLOCK,
            ),
        )
    )

    project_tracker_row_deviation_from_setpoint_deg_d = Field(
        TrackerDeviationFromSetpointCalc(
            position_var=Validate.tracker_row_position_deg_5m.var,
            setpoint_var=Validate.tracker_row_setpoint_deg_5m.var,
            time_combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.TRACKER_ROW,
            ),
        )
    )

    tracker_row_setpoint_deviation_from_median_deg_d = Field(
        TrackerSetpointDeviationFromMedianCalc(
            setpoint_var=Validate.tracker_row_setpoint_deg_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    block_tracker_setpoint_deviation_from_median_deg_d = Field(
        TrackerSetpointDeviationFromMedianCalc(
            setpoint_var=Validate.tracker_row_setpoint_deg_5m.var,
            time_combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.TRACKER_ROW,
                parent_device_axis=DeviceType.PV_BLOCK,
            ),
        )
    )

    project_tracker_row_setpoint_deviation_from_median_deg_d = Field(
        TrackerSetpointDeviationFromMedianCalc(
            setpoint_var=Validate.tracker_row_setpoint_deg_5m.var,
            time_combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.TRACKER_ROW,
            ),
        )
    )

    # ============================================================================
    # Energy Aggregations (Daily Sum)
    # ============================================================================
    # Aggregates energy metrics from 5-minute to daily by summing values

    project_energy_curtailed_kwh_d = _aggregate(
        var=Calculate.project_energy_curtailed_kwh_5m.var,
        agg=Aggregation.SUM,
    )

    project_energy_expected_best_kwh_d = _aggregate(
        var=Calculate.project_energy_expected_best_kwh_5m.var,
        agg=Aggregation.SUM,
    )

    pv_inverter_module_energy_kwh_d = _aggregate(
        var=Calculate.pv_inverter_module_energy_kwh_5m.var,
        agg=Aggregation.SUM,
    )

    project_energy_from_pcs_module_kwh_d = _aggregate(
        var=Calculate.pv_inverter_module_energy_kwh_5m.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.PV_INVERTER_MODULE,
    )

    pv_inverter_energy_production_kwh_d = _aggregate(
        var=Calculate.pv_inverter_energy_production_kwh_5m.var,
        agg=Aggregation.SUM,
    )

    project_energy_production_pcs_kwh_d = _aggregate(
        var=Calculate.pv_inverter_energy_production_kwh_5m.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.PV_INVERTER,
    )

    project_energy_production_kwh_d = _aggregate(
        var=Calculate.project_energy_production_kwh_5m.var,
        agg=Aggregation.SUM,
    )

    project_specific_yield_d = Field(
        QuotientCalc(
            numerator_var=project_energy_production_kwh_d.var,
            denominator_var=Validate.project_power_capacity_dc_kw.var,
        )
    )

    # ============================================================================
    # Field Health and Availability Calculations
    # ============================================================================
    # Calculates health metrics for DC combiners and mechanical availability

    pv_dc_combiner_field_health_d = Field(
        CalcProcess(
            calc=DcFieldHealthCalc(
                current_combiner_var=Download.time_series.pv_dc_combiner_current_amps_5m.var,
                power_capacity_dc_combiner_var=Validate.pv_dc_combiner_power_capacity_dc_kw.var,
                time_combiner_model=_5min_to_daily(),
            ),
            process=FilterToRangeProcess(min_value=-0.1, max_value=1.2),
        )
    )

    project_avg_pv_dc_combiner_field_health_d = Field(
        CalcProcess(
            calc=WeightedAverageCalc(
                array_var=pv_dc_combiner_field_health_d.var,
                weights_var=Validate.pv_dc_combiner_power_capacity_dc_kw.var,
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    pv_inverter_mechanical_availability_d = Field(
        CalcProcess(
            calc=MechanicalAvailabilityCalc(
                power_kw_var=Validate.pv_inverter_active_power_ac_kw_5m.var,
                met_station_poa_irradiance_w_m2_var=Validate.met_station_irradiance_poa_w_m2_5m.var,
                poa_threshold=90,
                time_combiner_model=_5min_to_daily(),
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    project_mechanical_availability_pcs_d = Field(
        CalcProcess(
            calc=MechanicalAvailabilityCalc(
                power_kw_var=Validate.pv_inverter_active_power_ac_kw_5m.var,
                met_station_poa_irradiance_w_m2_var=Validate.met_station_irradiance_poa_w_m2_5m.var,
                poa_threshold=90,
                time_combiner_model=_5min_to_daily(
                    child_device_axis=DeviceType.PV_INVERTER,
                ),
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    pv_dc_combiner_mechanical_availability_d = Field(
        CalcProcess(
            calc=CombinerMechanicalAvailabilityCalc(
                pcs_power_kw_var=Validate.pv_inverter_active_power_ac_kw_5m.var,
                combiner_current_amps_var=Download.time_series.pv_dc_combiner_current_amps_5m.var,
                met_station_poa_irradiance_w_m2_var=Validate.met_station_irradiance_poa_w_m2_5m.var,
                combiner_to_pcs_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.PV_DC_COMBINER,
                    parent_device_axis=DeviceType.PV_INVERTER,
                ),
                time_combiner_model=_5min_to_daily(),
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    project_combiner_mechanical_availability_d = Field(
        CalcProcess(
            calc=CombinerMechanicalAvailabilityCalc(
                pcs_power_kw_var=Validate.pv_inverter_active_power_ac_kw_5m.var,
                combiner_current_amps_var=Download.time_series.pv_dc_combiner_current_amps_5m.var,
                met_station_poa_irradiance_w_m2_var=Validate.met_station_irradiance_poa_w_m2_5m.var,
                combiner_to_pcs_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.PV_DC_COMBINER,
                    parent_device_axis=DeviceType.PV_INVERTER,
                ),
                time_combiner_model=_5min_to_daily(
                    child_device_axis=DeviceType.PV_DC_COMBINER,
                ),
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    # ============================================================================
    # Module State of Health Calculations
    # ============================================================================
    # Calculates module state of health from daily data

    pv_dc_combiner_module_excess_degradation_d = Field(
        CalcProcess(
            calc=PvDcCombinerModuleExcessDegradationCalc(
                met_station_irradiance_poa_w_m2_5m_var=Validate.met_station_irradiance_poa_w_m2_5m.var,
                project_theoretical_poa_irradiance_w_m2_5m_var=Calculate.project_theoretical_poa_irradiance_w_m2_5m.var,
                project_meter_power_kw_5m_var=Validate.project_active_power_meter_kw_5m.var,
                project_poi_limit_kw_var=Download.project_attributes.project_poi_limit_kw.var,
                pv_inverter_ac_power_kw_5m_var=Validate.pv_inverter_active_power_ac_kw_5m.var,
                pv_inverter_ac_power_capacity_kw_var=Validate.pv_inverter_ac_capacity_kw.var,
                pv_inverter_reactive_power_kvar_5m_var=Download.time_series.pv_inverter_reactive_power_kvar_5m.var,
                pv_inverter_module_voltage_v_5m_var=Validate.pv_inverter_module_voltage_v_5m.var,
                pv_inverter_module_power_kw_5m_var=Download.time_series.pv_inverter_module_power_ac_kw_5m.var,
                pv_inverter_module_power_capacity_kw_var=Download.device_attributes.pv_inverter_module_power_ac_capacity_kw.var,
                block_tracker_deviation_from_setpoint_deg_d_var=block_tracker_deviation_from_setpoint_deg_d.var,
                block_tracker_setpoint_deviation_from_median_deg_d_var=block_tracker_setpoint_deviation_from_median_deg_d.var,
                pv_dc_combiner_field_health_d_var=pv_dc_combiner_field_health_d.var,
                pv_dc_combiner_current_amps_5m_var=Download.time_series.pv_dc_combiner_current_amps_5m.var,
                pv_dc_combiner_expected_energy_kwh_5m_var=Calculate.pv_dc_combiner_energy_expected_best_kwh_5m.var,
                daily_combiner_model=_5min_to_daily(),
                broadcast_pcs_to_combiner_model=CoordCombinerModel(
                    parent_device_axis=DeviceType.PV_INVERTER,
                    child_device_axis=DeviceType.PV_DC_COMBINER,
                ),
                broadcast_block_to_combiner_model=CoordCombinerModel(
                    parent_device_axis=DeviceType.PV_BLOCK,
                    child_device_axis=DeviceType.PV_DC_COMBINER,
                ),
                module_to_pcs_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.PV_INVERTER_MODULE,
                    parent_device_axis=DeviceType.PV_INVERTER,
                ),
                final_time_combiner_model=_5min_to_daily(),
                pv_inverter_ac_power_setpoint_kw_5m_var=Validate.pv_inverter_active_power_setpoint_kw_5m.var,
                pv_inverter_voltage_v_5m_var=Validate.pv_inverter_voltage_v_5m.var,
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    project_module_excess_degradation_d = _device_aggregate(
        var=pv_dc_combiner_module_excess_degradation_d.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.PV_DC_COMBINER,
    )

    # ============================================================================
    # Performance Metrics
    # ============================================================================
    # Calculates performance index and performance ratio from energy and capacity data

    project_performance_index_d = Field(
        PerformanceIndexCalc(
            expected_energy_var=Calculate.project_energy_expected_best_kwh_5m.var,
            actual_energy_var=Calculate.project_energy_production_kwh_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    project_performance_ratio_d = Field(
        CalcProcess(
            calc=PerformanceRatioCalc(
                energy_var=Calculate.project_energy_production_kwh_5m.var,
                power_capacity_var=Validate.project_power_capacity_dc_kw.var,
                insolation_poa_var=Calculate.project_insolation_poa_kwh_m2_5m.var,
                combiner_model=_5min_to_daily(),
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )

    # ============================================================================
    # Contractual Metrics
    # ============================================================================
    # Calculates contractual metrics from energy and capacity data

    # Solv Guaranteed Availability

    project_solv_period_kwh_produced_d = Field(
        SolvPeriodKwhProducedCalc(
            project_irradiance_poa_w_m2_5m_var=Calculate.project_irradiance_poa_w_m2_5m.var,
            project_meter_power_kw_5m_var=Validate.project_active_power_meter_kw_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    project_solv_period_kwh_lost_d = Field(
        SolvPeriodKwhLostCalc(
            project_irradiance_poa_w_m2_5m_var=Calculate.project_irradiance_poa_w_m2_5m.var,
            unit_power_ac_kw_5m_var=Validate.pv_inverter_active_power_ac_kw_5m.var,
            unit_power_setpoint_kw_5m_var=Validate.pv_inverter_active_power_setpoint_kw_5m.var,
            project_meter_power_kw_5m_var=Validate.project_active_power_meter_kw_5m.var,
            unit_ac_capacity_kw_var=Validate.pv_inverter_ac_capacity_kw.var,
            unit_dc_capacity_kw_var=Validate.pv_inverter_dc_capacity_kw.var,
            project_expected_energy_kwh_5m_var=Calculate.project_energy_expected_best_kwh_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    project_solv_guarantee_availability_d = Field(
        CalcProcess(
            calc=SolvGuaranteeAvailabilityCalc(
                period_kwh_produced_var=project_solv_period_kwh_produced_d.var,
                period_kwh_lost_var=project_solv_period_kwh_lost_d.var,
            ),
            process=FilterToRangeProcess(min_value=0, max_value=1),
        )
    )
