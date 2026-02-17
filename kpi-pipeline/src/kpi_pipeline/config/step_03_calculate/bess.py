from kpi_pipeline.base.field import Field
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate import Validate
from kpi_pipeline.services.calc import (
    CalcProcess,
    LinearCombinationCalc,
    ProcessCalc,
    QuotientCalc,
    SelectCalc,
)
from kpi_pipeline.services.process import (
    CastTypeProcess,
    ClampProcess,
    DiffProcess,
    FilterToRangeProcess,
    FromRateOfChangeToTotalProcess,
    IsChargingProcess,
    IsDischargingProcess,
    IsIdlingProcess,
    ProcessList,
    RestingSocProcess,
    ScaleOffsetProcess,
)
from kpi_pipeline.services.schema import AddCalculationsSchema


def _c_rate(power: str, energy_capacity: str) -> Field:
    return Field(
        QuotientCalc(numerator_var=power, denominator_var=energy_capacity),
    )


def _dod(soc: str) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=soc),
            process=ScaleOffsetProcess(scale=-1, offset=1),
        )
    )


def _incremental_diff(field: str) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=field),
            process=DiffProcess(),
        ),
    )


def _time_hours(filter_field) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=filter_field),
            process=ProcessList(
                steps=[
                    CastTypeProcess(dtype="float64"),
                    FromRateOfChangeToTotalProcess(time_unit_seconds=3600),
                ],
            ),
        ),
    )


def _c_rate_charging(c_rate_field) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=c_rate_field),
            process=ProcessList(
                steps=[
                    FilterToRangeProcess(max_value=-0.01),
                    ScaleOffsetProcess(scale=-1),
                ]
            ),
        ),
    )


def _c_rate_discharging(c_rate_field) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=c_rate_field),
            process=FilterToRangeProcess(min_value=0.01),
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
        CalcProcess(
            calc=SelectCalc(var=Validate.bess_string_soh_5m.var),
            process=ProcessList(steps=[DiffProcess(), ScaleOffsetProcess(scale=-1)]),
        ),
    )

    bess_bank_dod_5m = _dod(Validate.bess_bank_soc_5m.var)

    project_dod_5m = _dod(Validate.project_soc_5m.var)

    bess_string_dod_5m = _dod(Validate.bess_string_soc_5m.var)

    project_energy_charged_kwh_5m = Field(
        CalcProcess(
            calc=SelectCalc(var=Validate.project_power_kw_5m.var),
            process=ProcessList(
                steps=[
                    ClampProcess(max_value=0),
                    ScaleOffsetProcess(scale=-1 / 12),
                ]
            ),
        )
    )

    project_energy_discharged_kwh_5m = Field(
        CalcProcess(
            calc=SelectCalc(var=Validate.project_power_kw_5m.var),
            process=ProcessList(
                steps=[
                    ClampProcess(min_value=0),
                    ScaleOffsetProcess(scale=1 / 12),
                ]
            ),
        )
    )

    bess_string_energy_charged_kwh_5m = _incremental_diff(
        Download.time_series.bess_string_total_energy_charged_kwh_5m.var
    )

    bess_string_energy_discharged_kwh_5m = _incremental_diff(
        Download.time_series.bess_string_total_energy_discharged_kwh_5m.var
    )

    bess_string_energy_kwh_5m = Field(
        LinearCombinationCalc(
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
        ProcessCalc(
            var=bess_pcs_c_rate_5m.var,
            process=IsChargingProcess(),
        )
    )

    bess_pcs_is_discharging_5m = Field(
        ProcessCalc(
            var=bess_pcs_c_rate_5m.var,
            process=IsDischargingProcess(),
        )
    )

    bess_pcs_is_idling_5m = Field(
        ProcessCalc(
            var=bess_pcs_c_rate_5m.var,
            process=IsIdlingProcess(),
        )
    )

    # Project

    project_is_charging_5m = Field(
        ProcessCalc(
            var=project_c_rate_5m.var,
            process=IsChargingProcess(),
        )
    )

    project_is_discharging_5m = Field(
        ProcessCalc(
            var=project_c_rate_5m.var,
            process=IsDischargingProcess(),
        )
    )

    project_is_idling_5m = Field(
        ProcessCalc(
            var=project_c_rate_5m.var,
            process=IsIdlingProcess(),
        )
    )

    #########################################################

    bess_bank_resting_soc_5m = Field(
        ProcessCalc(
            var=Validate.bess_bank_soc_5m.var,
            process=RestingSocProcess(threshold=0.01),
        )
    )

    bess_block_resting_soc_5m = Field(
        ProcessCalc(
            var=Validate.bess_block_soc_5m.var,
            process=RestingSocProcess(threshold=0.01),
        )
    )

    project_resting_soc_5m = Field(
        ProcessCalc(
            var=Validate.project_soc_5m.var,
            process=RestingSocProcess(threshold=0.01),
        )
    )

    bess_string_resting_soc_5m = Field(
        ProcessCalc(
            var=Validate.bess_string_soc_5m.var,
            process=RestingSocProcess(threshold=0.01),
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
