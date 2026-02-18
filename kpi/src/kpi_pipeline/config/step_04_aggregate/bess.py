from core.enumerations import DeviceType

from kpi_pipeline.base.enums import Aggregation
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import CoordCombinerModel
from kpi_pipeline.config.helper_fields import (
    _5min_to_daily,
    _aggregate,
    _device_aggregate,
    _resample_groupby,
)
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.config.step_03_calculate import Calculate
from kpi_pipeline.services.calc import (
    AccumulateEnergyThenFilterByCapacityCalc,
    AverageWhileChargingCalc,
    AverageWhileDischargingCalc,
    BessStringCompleteAvailabilityCalc,
    CalcProcess,
    ChargingCyclesFromSocCalc,
    CycleCountFromSocCalc,
    DailyAverageCRateCalc,
    DailyAverageCRateChargingCalc,
    DischargingCyclesFromSocCalc,
    MaximumContinuousDischargeCalc,
    ProcessCalc,
)
from kpi_pipeline.services.process import (
    AvailabilityProcess,
    FilterToRangeProcess,
    ProcessList,
)
from kpi_pipeline.services.schema import AddCalculationsSchema


class AggregateBESS(AddCalculationsSchema):
    # ============================================================================
    # Availability Calculations
    # ============================================================================

    bess_bank_availability_d = Field(
        ProcessCalc(
            var=Download.status.bess_bank_status_5m.var,
            process=ProcessList(
                steps=[
                    AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(),
                    ),
                    FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    project_bess_bank_availability_d = Field(
        ProcessCalc(
            var=Download.status.bess_bank_status_5m.var,
            process=ProcessList(
                steps=[
                    AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(
                            child_device_axis=DeviceType.BESS_BANK,
                        ),
                    ),
                    FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    bess_pcs_availability_d = Field(
        ProcessCalc(
            var=Download.status.bess_pcs_status_5m.var,
            process=ProcessList(
                steps=[
                    AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(),
                    ),
                    FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    project_bess_pcs_availability_d = Field(
        ProcessCalc(
            var=Download.status.bess_pcs_status_5m.var,
            process=ProcessList(
                steps=[
                    AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(
                            child_device_axis=DeviceType.BESS_PCS,
                        ),
                    ),
                    FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    bess_pcs_module_availability_d = Field(
        ProcessCalc(
            var=Download.status.bess_pcs_module_offline_status_5m.var,
            process=ProcessList(
                steps=[
                    AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(),
                    ),
                ],
            ),
        )
    )

    project_bess_pcs_module_availability_d = Field(
        ProcessCalc(
            var=Download.status.bess_pcs_module_offline_status_5m.var,
            process=ProcessList(
                steps=[
                    AvailabilityProcess(
                        time_combiner_model=_5min_to_daily(
                            child_device_axis=DeviceType.BESS_PCS_MODULE,
                        ),
                    ),
                    FilterToRangeProcess(
                        min_value=0,
                        max_value=1,
                    ),
                ],
            ),
        )
    )

    bess_string_complete_availability_d = Field(
        CalcProcess(
            calc=BessStringCompleteAvailabilityCalc(
                bess_string_status_var=Download.status.bess_string_status_5m.var,
                bess_bank_status_var=Download.status.bess_bank_status_5m.var,
                bess_pcs_status_var=Download.status.bess_pcs_status_5m.var,
                string_to_bank_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.BESS_STRING,
                    parent_device_axis=DeviceType.BESS_BANK,
                ),
                string_to_pcs_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.BESS_STRING,
                    parent_device_axis=DeviceType.BESS_PCS,
                ),
                time_combiner_model=_5min_to_daily(),
            ),
            process=FilterToRangeProcess(
                min_value=0,
                max_value=1,
            ),
        )
    )

    project_complete_availability_d = Field(
        CalcProcess(
            calc=BessStringCompleteAvailabilityCalc(
                bess_string_status_var=Download.status.bess_string_status_5m.var,
                bess_bank_status_var=Download.status.bess_bank_status_5m.var,
                bess_pcs_status_var=Download.status.bess_pcs_status_5m.var,
                string_to_bank_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.BESS_STRING,
                    parent_device_axis=DeviceType.BESS_BANK,
                ),
                string_to_pcs_combiner_model=CoordCombinerModel(
                    child_device_axis=DeviceType.BESS_STRING,
                    parent_device_axis=DeviceType.BESS_PCS,
                ),
                time_combiner_model=_5min_to_daily(
                    child_device_axis=DeviceType.BESS_STRING,
                ),
            ),
            process=FilterToRangeProcess(
                min_value=0,
                max_value=1,
            ),
        )
    )

    # ============================================================================
    # C-Rate Calculations
    # ============================================================================
    # Aggregates C-rate (charge/discharge rate relative to capacity) from 5-minute
    # to daily, including overall averages and averages during charging/discharging

    project_avg_pcs_c_rate_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_avg_c_rate_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_c_rate_d = _aggregate(
        var=Calculate.project_c_rate_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_pcs_c_rate_while_charging_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_charging_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_avg_c_rate_charging_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_charging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_c_rate_while_charging_d = _aggregate(
        var=Calculate.project_c_rate_charging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_pcs_c_rate_while_discharging_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_discharging_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_avg_c_rate_discharging_d = _aggregate(
        var=Calculate.bess_pcs_c_rate_discharging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_c_rate_while_discharging_d = _aggregate(
        var=Calculate.project_c_rate_discharging_5m.var,
        agg=Aggregation.MEAN,
    )

    # ============================================================================
    # String Current Calculations
    # ============================================================================
    # Aggregates string current from 5-minute to daily, including averages, min/max,
    # and averages during charging/discharging periods

    bess_string_avg_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_string_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )

    bess_string_max_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MAX,
    )
    project_max_string_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
    )

    bess_string_min_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MIN,
    )
    project_min_string_current_amps_d = _aggregate(
        var=Validate.bess_string_current_amps_5m.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
    )

    bess_string_avg_current_while_charging_amps_d = Field(
        AverageWhileChargingCalc(
            x_var=Validate.bess_string_current_amps_5m.var,
            c_rate_var=Calculate.bess_string_c_rate_5m.var,
            combiner_model=_5min_to_daily(),
        )
    )

    project_avg_string_current_while_charging_amps_d = Field(
        AverageWhileChargingCalc(
            x_var=Validate.bess_string_current_amps_5m.var,
            c_rate_var=Calculate.bess_string_c_rate_5m.var,
            combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.BESS_STRING,
            ),
        )
    )

    bess_string_avg_current_while_discharging_amps_d = Field(
        AverageWhileDischargingCalc(
            x_var=Validate.bess_string_current_amps_5m.var,
            c_rate_var=Calculate.bess_string_c_rate_5m.var,
            combiner_model=_5min_to_daily(),
        )
    )
    project_avg_string_current_while_discharging_amps_d = Field(
        AverageWhileDischargingCalc(
            x_var=Validate.bess_string_current_amps_5m.var,
            c_rate_var=Calculate.bess_string_c_rate_5m.var,
            combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.BESS_STRING,
            ),
        )
    )

    # ============================================================================
    # Cycle Calculations
    # ============================================================================
    # Calculates charging/discharging cycles and cycle counts from SOC data
    # aggregated from 5-minute to daily

    project_cycles_charging_d = Field(
        ChargingCyclesFromSocCalc(
            soc_5m_var=Validate.project_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    project_cycles_discharging_d = Field(
        DischargingCyclesFromSocCalc(
            soc_5m_var=Validate.project_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    bess_bank_cycle_count_d = Field(
        CycleCountFromSocCalc(
            soc_5m_var=Validate.bess_bank_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    bess_block_cycle_count_d = Field(
        CycleCountFromSocCalc(
            soc_5m_var=Validate.bess_block_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    bess_string_cycle_count_d = Field(
        CycleCountFromSocCalc(
            soc_5m_var=Validate.bess_string_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    project_cycle_count_d = Field(
        CycleCountFromSocCalc(
            soc_5m_var=Validate.project_soc_5m.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    project_avg_bank_cycle_count_d = _device_aggregate(
        var=bess_bank_cycle_count_d.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )

    project_avg_block_cycle_count_d = _device_aggregate(
        var=bess_block_cycle_count_d.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BLOCK,
    )

    project_avg_string_cycle_count_d = _device_aggregate(
        var=bess_string_cycle_count_d.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )

    # ============================================================================
    # Degradation and Depth of Discharge (DOD)
    # ============================================================================
    # Calculates string degradation and depth of discharge metrics

    project_total_string_degradation_d = _resample_groupby(
        field=Calculate.bess_string_degradation_5m.var,
        agg_resample=Aggregation.SUM,
        agg_groupby=Aggregation.MEAN,
        from_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_total_degradation_d = _aggregate(
        var=Calculate.bess_string_degradation_5m.var,
        agg=Aggregation.SUM,
    )

    bess_bank_avg_dod_d = _aggregate(
        var=Calculate.bess_bank_dod_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_bank_dod_d = _aggregate(
        var=Calculate.bess_bank_dod_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )

    project_avg_dod_d = _aggregate(
        var=Calculate.project_dod_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_string_dod_d = _aggregate(
        var=Calculate.bess_string_dod_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_avg_dod_d = _aggregate(
        var=Calculate.bess_string_dod_5m.var,
        agg=Aggregation.MEAN,
    )

    # ============================================================================
    # Energy Aggregations
    # ============================================================================
    # Aggregates energy metrics from 5-minute to daily by summing or accumulating
    # energy charged, discharged, and auxiliary energy consumption

    project_energy_aux_meter_kwh_d = Field(
        AccumulateEnergyThenFilterByCapacityCalc(
            data_var=Download.time_series.project_total_aux_energy_kwh_5m.var,
            time_combiner_model=_5min_to_daily(),
            capacity_var=Validate.project_energy_capacity_kwh.var,
            min_capacity_factor=-1.0,
            max_capacity_factor=1.0,
        )
    )

    project_energy_charged_kwh_d = _aggregate(
        var=Calculate.project_energy_charged_kwh_5m.var,
        agg=Aggregation.SUM,
    )

    bess_string_energy_charged_kwh_d = Field(
        AccumulateEnergyThenFilterByCapacityCalc(
            data_var=Download.time_series.bess_string_total_energy_charged_kwh_5m.var,
            time_combiner_model=_5min_to_daily(),
            capacity_var=Validate.bess_string_energy_capacity_kwh.var,
            min_capacity_factor=-1.0,
            max_capacity_factor=1.0,
        )
    )

    project_energy_discharged_kwh_d = _aggregate(
        var=Calculate.project_energy_discharged_kwh_5m.var,
        agg=Aggregation.SUM,
    )

    bess_string_energy_discharged_kwh_d = Field(
        AccumulateEnergyThenFilterByCapacityCalc(
            data_var=Download.time_series.bess_string_total_energy_discharged_kwh_5m.var,
            time_combiner_model=_5min_to_daily(),
            capacity_var=Validate.bess_string_energy_capacity_kwh.var,
            min_capacity_factor=-1.0,
            max_capacity_factor=1.0,
        )
    )

    project_energy_charged_string_kwh_d = _device_aggregate(
        var=bess_string_energy_charged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_STRING,
    )

    project_energy_discharged_string_kwh_d = _device_aggregate(
        var=bess_string_energy_discharged_kwh_d.var,
        agg=Aggregation.SUM,
        child_device_axis=DeviceType.BESS_STRING,
    )

    bess_string_avg_c_rate_d = Field(
        DailyAverageCRateCalc(
            daily_energy_charged_var=bess_string_energy_charged_kwh_d.var,
            daily_energy_discharged_var=bess_string_energy_discharged_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    project_avg_string_c_rate_d = Field(
        DailyAverageCRateCalc(
            daily_energy_charged_var=project_energy_charged_string_kwh_d.var,
            daily_energy_discharged_var=project_energy_discharged_string_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    bess_string_avg_c_rate_while_charging_d = Field(
        DailyAverageCRateChargingCalc(
            daily_energy_charged_var=bess_string_energy_charged_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    project_avg_string_c_rate_while_charging_d = Field(
        DailyAverageCRateChargingCalc(
            daily_energy_charged_var=project_energy_charged_string_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    bess_string_avg_c_rate_while_discharging_d = Field(
        DailyAverageCRateChargingCalc(
            daily_energy_charged_var=bess_string_energy_discharged_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    project_avg_string_c_rate_while_discharging_d = Field(
        DailyAverageCRateChargingCalc(
            daily_energy_charged_var=project_energy_discharged_string_kwh_d.var,
            energy_capacity_var=Validate.project_energy_capacity_kwh.var,
        )
    )

    # ============================================================================
    # Power Calculations (While Charging/Discharging)
    # ============================================================================
    # Calculates average power during charging and discharging periods

    bess_pcs_avg_power_while_charging_kw_d = Field(
        AverageWhileChargingCalc(
            x_var=Validate.bess_pcs_power_kw_5m.var,
            c_rate_var=Calculate.bess_pcs_c_rate_5m.var,
            combiner_model=_5min_to_daily(),
        )
    )
    project_avg_pcs_power_while_charging_kw_d = Field(
        AverageWhileChargingCalc(
            x_var=Validate.bess_pcs_power_kw_5m.var,
            c_rate_var=Calculate.bess_pcs_c_rate_5m.var,
            combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.BESS_PCS,
            ),
        )
    )

    bess_pcs_avg_power_while_discharging_kw_d = Field(
        AverageWhileDischargingCalc(
            x_var=Validate.bess_pcs_power_kw_5m.var,
            c_rate_var=Calculate.bess_pcs_c_rate_5m.var,
            combiner_model=_5min_to_daily(),
        )
    )
    project_avg_pcs_power_while_discharging_kw_d = Field(
        AverageWhileDischargingCalc(
            x_var=Validate.bess_pcs_power_kw_5m.var,
            c_rate_var=Calculate.bess_pcs_c_rate_5m.var,
            combiner_model=_5min_to_daily(
                child_device_axis=DeviceType.BESS_PCS,
            ),
        )
    )

    project_maximum_continuous_discharge_kwh_d = Field(
        MaximumContinuousDischargeCalc(
            energy_discharged_kwh_var=Calculate.project_energy_discharged_kwh_5m.var,
            energy_capacity_kwh_var=Validate.project_energy_capacity_kwh.var,
            time_combiner_model=_5min_to_daily(),
        )
    )

    # ============================================================================
    # Time Aggregations
    # ============================================================================
    # Aggregates time spent in different operational states (charging, discharging,
    # idling) and calculates portion of time in each state

    project_total_pcs_time_charging_hours_d = _resample_groupby(
        field=Calculate.bess_pcs_time_charging_hours_5m.var,
        agg_resample=Aggregation.SUM,
        agg_groupby=Aggregation.MEAN,
        from_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_total_time_charging_hours_d = _aggregate(
        var=Calculate.bess_pcs_time_charging_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_time_charging_hours_d = _aggregate(
        var=Calculate.project_time_charging_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_pcs_time_while_discharging_hours_d = _resample_groupby(
        field=Calculate.bess_pcs_time_discharging_hours_5m.var,
        agg_resample=Aggregation.SUM,
        agg_groupby=Aggregation.MEAN,
        from_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_total_time_discharging_hours_d = _aggregate(
        var=Calculate.bess_pcs_time_discharging_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_time_while_discharging_hours_d = _aggregate(
        var=Calculate.project_time_discharging_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_pcs_time_idling_hours_d = _resample_groupby(
        field=Calculate.bess_pcs_time_idling_hours_5m.var,
        agg_resample=Aggregation.SUM,
        agg_groupby=Aggregation.MEAN,
        from_device_axis=DeviceType.BESS_PCS,
    )
    bess_pcs_total_time_idling_hours_d = _aggregate(
        var=Calculate.bess_pcs_time_idling_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_total_time_idling_hours_d = _aggregate(
        var=Calculate.project_time_idling_hours_5m.var,
        agg=Aggregation.SUM,
    )

    project_portion_of_time_charging_d = _aggregate(
        var=Calculate.project_is_charging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_portion_of_time_discharging_d = _aggregate(
        var=Calculate.project_is_discharging_5m.var,
        agg=Aggregation.MEAN,
    )

    project_portion_of_time_idling_d = _aggregate(
        var=Calculate.project_is_idling_5m.var,
        agg=Aggregation.MEAN,
    )

    # ============================================================================
    # State of Charge (SOC) Aggregations
    # ============================================================================
    # Aggregates state of charge from 5-minute to daily at various device levels

    bess_bank_avg_soc_d = _aggregate(
        var=Validate.bess_bank_soc_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_bank_soc_d = _aggregate(
        var=Validate.bess_bank_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )
    bess_block_avg_soc_d = _aggregate(
        var=Validate.bess_block_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_block_soc_d = _aggregate(
        var=Validate.bess_block_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BLOCK,
    )

    project_avg_soc_d = _aggregate(
        var=Validate.project_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    ##
    # string SOC
    #

    # average
    project_avg_string_soc_d = _aggregate(
        var=Validate.bess_string_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_avg_soc_d = _aggregate(
        var=Validate.bess_string_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    # ============================================================================
    # Resting State of Charge (SOC) Aggregations
    # ============================================================================
    # Aggregates resting SOC (SOC when system is not actively charging/discharging)
    # from 5-minute to daily at various device levels

    bess_bank_avg_resting_soc_d = _aggregate(
        var=Calculate.bess_bank_resting_soc_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_bank_resting_soc_d = _aggregate(
        var=Calculate.bess_bank_resting_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )

    bess_block_avg_resting_soc_d = _aggregate(
        var=Calculate.bess_block_resting_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    project_avg_block_resting_soc_d = _aggregate(
        var=Calculate.bess_block_resting_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BLOCK,
    )

    project_avg_resting_soc_d = _aggregate(
        var=Calculate.project_resting_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    ##
    # string resting SOC
    #

    # average

    project_avg_string_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_avg_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MEAN,
    )

    # max

    bess_string_max_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MAX,
    )
    project_max_string_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
    )

    # min

    bess_string_min_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MIN,
    )
    project_min_string_resting_soc_d = _aggregate(
        var=Calculate.bess_string_resting_soc_5m.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
    )

    # enclosure aggregations from string
    # enclosure values are derived from the string values

    bess_enclosure_avg_resting_soc_d = _device_aggregate(
        var=bess_string_avg_resting_soc_d.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
        parent_device_axis=DeviceType.BESS_ENCLOSURE,
    )

    bess_enclosure_max_resting_soc_d = _device_aggregate(
        var=bess_string_max_resting_soc_d.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
        parent_device_axis=DeviceType.BESS_ENCLOSURE,
    )

    bess_enclosure_min_resting_soc_d = _device_aggregate(
        var=bess_string_min_resting_soc_d.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
        parent_device_axis=DeviceType.BESS_ENCLOSURE,
    )

    # ============================================================================
    # State of Health (SOH) Aggregations
    # ============================================================================
    # Aggregates state of health from 5-minute to daily at bank and string levels

    bess_bank_avg_soh_d = _aggregate(
        var=Validate.bess_bank_soh_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_bank_soh_d = _aggregate(
        var=Validate.bess_bank_soh_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_BANK,
    )
    project_avg_string_soh_d = _aggregate(
        var=Validate.bess_string_soh_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_avg_soh_d = _aggregate(
        var=Validate.bess_string_soh_5m.var,
        agg=Aggregation.MEAN,
    )

    # ============================================================================
    # Temperature Aggregations
    # ============================================================================
    # Aggregates cell and module temperatures from 5-minute to daily, including
    # averages, minimums, and maximums

    bess_string_avg_cell_temp_c_d = _aggregate(
        var=Validate.bess_string_avg_cell_temp_c_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_string_cell_temp_c_d = _aggregate(
        var=Validate.bess_string_avg_cell_temp_c_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_min_cell_temp_c_d = _aggregate(
        var=Validate.bess_string_min_cell_temp_c_5m.var,
        agg=Aggregation.MIN,
    )
    project_min_string_cell_temp_c_d = _aggregate(
        var=Validate.bess_string_min_cell_temp_c_5m.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_max_cell_temp_c_d = _aggregate(
        var=Validate.bess_string_max_cell_temp_c_5m.var,
        agg=Aggregation.MAX,
    )
    project_max_string_cell_temp_c_d = _aggregate(
        var=Validate.bess_string_max_cell_temp_c_5m.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
    )

    project_avg_string_module_temp_c_d = _aggregate(
        var=Validate.bess_string_avg_module_temp_c_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_avg_module_temp_c_d = _aggregate(
        var=Validate.bess_string_avg_module_temp_c_5m.var,
        agg=Aggregation.MEAN,
    )

    project_min_string_module_temp_c_d = _aggregate(
        var=Validate.bess_string_min_module_temp_c_5m.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_min_module_temp_c_d = _aggregate(
        var=Validate.bess_string_min_module_temp_c_5m.var,
        agg=Aggregation.MIN,
    )

    project_max_string_module_temp_c_d = _aggregate(
        var=Validate.bess_string_max_module_temp_c_5m.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_max_module_temp_c_d = _aggregate(
        var=Validate.bess_string_max_module_temp_c_5m.var,
        agg=Aggregation.MAX,
    )

    # ============================================================================
    # Voltage Aggregations
    # ============================================================================
    # Aggregates cell voltage from 5-minute to daily, including averages,
    # minimums, and maximums

    bess_string_avg_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_avg_cell_voltage_v_5m.var,
        agg=Aggregation.MEAN,
    )
    project_avg_string_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_avg_cell_voltage_v_5m.var,
        agg=Aggregation.MEAN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_min_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_min_cell_voltage_v_5m.var,
        agg=Aggregation.MIN,
    )
    project_min_string_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_min_cell_voltage_v_5m.var,
        agg=Aggregation.MIN,
        child_device_axis=DeviceType.BESS_STRING,
    )
    bess_string_max_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_max_cell_voltage_v_5m.var,
        agg=Aggregation.MAX,
    )
    project_max_string_cell_voltage_v_d = _aggregate(
        var=Validate.bess_string_max_cell_voltage_v_5m.var,
        agg=Aggregation.MAX,
        child_device_axis=DeviceType.BESS_STRING,
    )
