from core.enumerations import DeviceType

import kpi_pipeline.services.calc as calc
import kpi_pipeline.services.process as process
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import CoordCombinerModel
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.services.schema import AddCalculationsSchema


def _c_rate(power: str, energy_capacity: str) -> Field:
    return Field(
        calc.QuotientCalc(numerator_var=power, denominator_var=energy_capacity),
    )


def _dod(soc: str) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=soc),
            process=process.ScaleOffsetProcess(scale=-1, offset=1),
        )
    )


def _fill_energy_accumulator(field: str) -> Field:
    return Field(
        calc.ProcessCalc(
            var=field,
            process=process.ProcessList(
                steps=[process.ForwardFillProcess(), process.BackwardFillProcess()],
            ),
        )
    )


def _energy_accumulator(field: str) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=field),
            process=process.ProcessList(
                steps=[
                    process.DiffProcess(),
                    process.ClampProcess(min_value=0),
                ],
            ),
        ),
    )


def _time_hours(filter_field) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=filter_field),
            process=process.ProcessList(
                steps=[
                    process.CastTypeProcess(dtype="float64"),
                    process.FromRateOfChangeToTotalProcess(time_unit_seconds=3600),
                ],
            ),
        ),
    )


def _c_rate_charging(c_rate_field) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=c_rate_field),
            process=process.ProcessList(
                steps=[
                    process.FilterToRangeProcess(max_value=-0.01),
                    process.ScaleOffsetProcess(scale=-1),
                ]
            ),
        ),
    )


def _c_rate_discharging(c_rate_field) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=c_rate_field),
            process=process.FilterToRangeProcess(min_value=0.01),
        ),
    )


class CalculateBESS(AddCalculationsSchema):
    bess_pcs_c_rate_5m = _c_rate(
        Validate.bess_pcs_power_kw_5m.var,
        Validate.bess_pcs_energy_capacity_kwh.var,
    )

    project_c_rate_5m = _c_rate(
        Validate.project_power_kw_5m.var,
        Validate.project_energy_capacity_kwh.var,
    )

    bess_string_c_rate_5m = _c_rate(
        Validate.bess_string_power_kw_5m.var,
        Validate.bess_string_energy_capacity_kwh.var,
    )

    bess_string_degradation_5m = Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=Validate.bess_string_soh_5m.var),
            process=process.ProcessList(
                steps=[process.DiffProcess(), process.ScaleOffsetProcess(scale=-1)]
            ),
        ),
    )

    ##
    # SOC
    #

    bess_bank_dod_5m = _dod(Validate.bess_bank_soc_5m.var)

    project_dod_5m = _dod(Validate.project_soc_5m.var)

    bess_string_dod_5m = _dod(Validate.bess_string_soc_5m.var)

    bess_project_string_soc_variance_5m = Field(
        calc.VarianceCalc(
            x_var=Validate.bess_string_soc_5m.var,
            combiner_model=CoordCombinerModel(child_device_axis=DeviceType.BESS_STRING),
        )
    )

    bess_pcs_string_soc_variance_5m = Field(
        calc.VarianceCalc(
            x_var=Validate.bess_string_soc_5m.var,
            combiner_model=CoordCombinerModel(
                child_device_axis=DeviceType.BESS_STRING,
                parent_device_axis=DeviceType.BESS_PCS,
            ),
        )
    )

    ##
    # backfill and forward fill the energy accumulators to remove NaNs
    #

    # meter

    meter_total_consumed_energy_filled_5m = _fill_energy_accumulator(
        Download.time_series.meter_total_consumed_energy_kwh_5m.var
    )

    meter_total_delivered_energy_filled_5m = _fill_energy_accumulator(
        Download.time_series.meter_total_delivered_energy_kwh_5m.var
    )

    # pcs module

    bess_pcs_module_total_energy_charged_filled_5m = _fill_energy_accumulator(
        Download.time_series.bess_pcs_module_total_energy_charged_kwh_5m.var
    )

    bess_pcs_module_total_energy_discharged_filled_5m = _fill_energy_accumulator(
        Download.time_series.bess_pcs_module_total_energy_discharged_kwh_5m.var
    )

    ##
    # Calculate energy on a 5-minute level (not totals)
    #

    meter_consumed_energy_kwh_5m = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=meter_total_consumed_energy_filled_5m.var,
            power_capacity_var=Validate.project_power_capacity_kw.var,
            max_capacity_factor=1 / 12,  # 12 steps per hour
        )
    )

    meter_delivered_energy_kwh_5m = Field(
        calc.DiffAndFilterCalc(
            energy_total_var=meter_total_delivered_energy_filled_5m.var,
            power_capacity_var=Validate.project_power_capacity_kw.var,
            max_capacity_factor=1 / 12,  # 12 steps per hour
        )
    )

    bess_string_energy_charged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_string_total_energy_charged_kwh_5m.var
    )

    bess_string_energy_discharged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_string_total_energy_discharged_kwh_5m.var
    )

    bess_pcs_energy_charged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_pcs_total_energy_charged_kwh_5m.var
    )

    bess_pcs_energy_discharged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_pcs_total_energy_discharged_kwh_5m.var
    )

    bess_pcs_module_energy_discharged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_pcs_module_total_energy_discharged_kwh_5m.var
    )

    bess_pcs_module_energy_charged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_pcs_module_total_energy_charged_kwh_5m.var
    )

    bess_circuit_energy_charged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_circuit_total_energy_charged_kwh_5m.var
    )

    bess_circuit_energy_discharged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_circuit_total_energy_discharged_kwh_5m.var
    )

    bess_string_energy_kwh_5m = Field(
        calc.LinearCombinationCalc(
            vars=[
                bess_string_energy_charged_kwh_5m.var,
                bess_string_energy_discharged_kwh_5m.var,
            ],
            coefficients=[1, -1],
        ),
    )

    ##
    # boolean charging, discharging, idling
    #########################################################

    # PCS

    bess_pcs_is_charging_5m = Field(
        calc.ProcessCalc(
            var=bess_pcs_c_rate_5m.var,
            process=process.IsChargingProcess(),
        )
    )

    bess_pcs_is_discharging_5m = Field(
        calc.ProcessCalc(
            var=bess_pcs_c_rate_5m.var,
            process=process.IsDischargingProcess(),
        )
    )

    bess_pcs_is_idling_5m = Field(
        calc.ProcessCalc(
            var=bess_pcs_c_rate_5m.var,
            process=process.IsIdlingProcess(),
        )
    )

    #########################################################
    # PCS Module

    bess_pcs_module_is_offline_5m = Field(
        calc.OrListCalc(
            vars=[
                Download.status.bess_pcs_module_offline_status_5m.var,
                Download.status.bess_pcs_module_offline_alarm_5m.var,
            ]
        )
    )

    # Project

    project_is_charging_5m = Field(
        calc.ProcessCalc(
            var=project_c_rate_5m.var,
            process=process.IsChargingProcess(),
        )
    )

    project_is_discharging_5m = Field(
        calc.ProcessCalc(
            var=project_c_rate_5m.var,
            process=process.IsDischargingProcess(),
        )
    )

    project_is_idling_5m = Field(
        calc.ProcessCalc(
            var=project_c_rate_5m.var,
            process=process.IsIdlingProcess(),
        )
    )

    #########################################################

    bess_bank_resting_soc_5m = Field(
        calc.ProcessCalc(
            var=Validate.bess_bank_soc_5m.var,
            process=process.RestingSocProcess(threshold=0.01),
        )
    )

    bess_block_resting_soc_5m = Field(
        calc.ProcessCalc(
            var=Validate.bess_block_soc_5m.var,
            process=process.RestingSocProcess(threshold=0.01),
        )
    )

    project_resting_soc_5m = Field(
        calc.ProcessCalc(
            var=Validate.project_soc_5m.var,
            process=process.RestingSocProcess(threshold=0.01),
        )
    )

    bess_string_resting_soc_5m = Field(
        calc.ProcessCalc(
            var=Validate.bess_string_soc_5m.var,
            process=process.RestingSocProcess(threshold=0.01),
        )
    )

    bess_pcs_time_charging_hours_5m = _time_hours(bess_pcs_is_charging_5m.var)

    project_time_charging_hours_5m = _time_hours(project_is_charging_5m.var)

    bess_pcs_time_discharging_hours_5m = _time_hours(bess_pcs_is_discharging_5m.var)

    project_time_discharging_hours_5m = _time_hours(project_is_discharging_5m.var)

    bess_pcs_time_idling_hours_5m = _time_hours(bess_pcs_is_idling_5m.var)

    project_time_idling_hours_5m = _time_hours(project_is_idling_5m.var)

    bess_pcs_c_rate_charging_5m = _c_rate_charging(bess_pcs_c_rate_5m.var)

    project_c_rate_charging_5m = _c_rate_charging(project_c_rate_5m.var)

    bess_pcs_c_rate_discharging_5m = _c_rate_discharging(bess_pcs_c_rate_5m.var)

    project_c_rate_discharging_5m = _c_rate_discharging(project_c_rate_5m.var)

    bess_pcs_module_offline_in_event_5m = Field(
        calc.ProcessCalc(
            var=Download.events.bess_pcs_module_offline_event_change_5m.var,
            process=process.EventChangeToInEventProcess(),
        )
    )
