from kpi_pipeline.base.field import Field
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate.utils import _capacity
from kpi_pipeline.services.calc import (
    CalcProcess,
    FilterByCapacityCalc,
    ProcessCalc,
    SelectCalc,
)
from kpi_pipeline.services.process import (
    FilterToRangeProcess,
    ProcessList,
    VerifyWithinRangeProcess,
)
from kpi_pipeline.services.schema import AddCalculationsSchema


def _energy_accumulator(field: str) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=field),
            process=FilterToRangeProcess(min_value=0, left_inclusive=False),
        )
    )


def _soc(field: str) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=field),
            process=ProcessList(
                steps=[
                    VerifyWithinRangeProcess(min_value=0, max_value=1),
                    FilterToRangeProcess(
                        min_value=0.0, max_value=1.0, left_inclusive=False
                    ),
                ]
            ),
        ),
    )


def _soh(var: str) -> Field:
    return Field(
        ProcessCalc(
            var=var,
            process=ProcessList(
                steps=[
                    VerifyWithinRangeProcess(min_value=0, max_value=1),
                    FilterToRangeProcess(min_value=0.2, max_value=1),
                ]
            ),
        )
    )


def _temperature(field: str) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=field),
            process=FilterToRangeProcess(min_value=1, max_value=150),
        ),
    )


def _voltage(field: str) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=field),
            process=FilterToRangeProcess(min_value=0, max_value=8),
        ),
    )


def _current(field: str) -> Field:
    return Field(
        CalcProcess(
            calc=SelectCalc(var=field),
            process=FilterToRangeProcess(min_value=-1000, max_value=1000),
        ),
    )


class ValidateBESS(AddCalculationsSchema):
    _update = True

    project_energy_capacity_kwh = _capacity(
        Download.project_attributes.project_energy_capacity_kwh.var
    )
    bess_pcs_energy_capacity_kwh = _capacity(
        Download.device_attributes.bess_pcs_energy_capacity_kwh.var
    )
    bess_string_energy_capacity_kwh = _capacity(
        Download.device_attributes.bess_string_energy_capacity_kwh.var
    )
    bess_pcs_total_energy_charged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_pcs_energy_charged_total_kwh_5m.var
    )
    bess_string_total_energy_charged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_string_total_energy_charged_kwh_5m.var
    )
    bess_pcs_total_energy_discharged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_pcs_total_energy_discharged_kwh_5m.var
    )
    bess_string_total_energy_discharged_kwh_5m = _energy_accumulator(
        Download.time_series.bess_string_total_energy_discharged_kwh_5m.var
    )
    bess_pcs_power_capacity_kw = _capacity(
        Download.device_attributes.bess_pcs_power_capacity_kw.var
    )
    bess_string_power_capacity_kw = _capacity(
        Download.device_attributes.bess_string_power_capacity_kw.var
    )

    bess_string_min_module_temp_c_5m = _temperature(
        Download.time_series.bess_string_min_module_temp_c_5m.var
    )
    bess_string_max_module_temp_c_5m = _temperature(
        Download.time_series.bess_string_max_module_temp_c_5m.var
    )
    bess_string_avg_module_temp_c_5m = _temperature(
        Download.time_series.bess_string_avg_module_temp_c_5m.var
    )

    bess_string_avg_cell_temp_c_5m = _temperature(
        Download.time_series.bess_string_avg_cell_temp_c_5m.var
    )
    bess_string_min_cell_temp_c_5m = _temperature(
        Download.time_series.bess_string_min_cell_temp_c_5m.var
    )
    bess_string_max_cell_temp_c_5m = _temperature(
        Download.time_series.bess_string_max_cell_temp_c_5m.var
    )

    # SOC validation
    bess_bank_soc_5m = _soc(Download.time_series.bess_bank_soc_5m.var)
    bess_block_soc_5m = _soc(Download.time_series.bess_block_soc_5m.var)
    bess_string_soc_5m = _soc(Download.time_series.bess_string_soc_5m.var)
    project_soc_5m = _soc(Download.time_series.project_soc_5m.var)

    # SOH validation
    bess_bank_soh_5m = _soh(Download.time_series.bess_bank_soh_5m.var)
    bess_string_soh_5m = _soh(Download.time_series.bess_string_soh_5m.var)

    # Power validation

    bess_pcs_power_kw_5m = Field(
        FilterByCapacityCalc(
            data_var=Download.time_series.bess_pcs_power_kw_5m.var,
            capacity_var=Download.device_attributes.bess_pcs_power_capacity_kw.var,
            min_capacity_factor=-1.0,
            max_capacity_factor=1.0,
        )
    )

    bess_string_power_kw_5m = Field(
        FilterByCapacityCalc(
            data_var=Download.time_series.bess_string_power_kw_5m.var,
            capacity_var=Download.device_attributes.bess_string_power_capacity_kw.var,
            min_capacity_factor=-1.0,
            max_capacity_factor=1.0,
        )
    )

    # Voltage validation
    bess_string_avg_cell_voltage_v_5m = _voltage(
        Download.time_series.bess_string_avg_cell_voltage_v_5m.var
    )
    bess_string_min_cell_voltage_v_5m = _voltage(
        Download.time_series.bess_string_min_cell_voltage_v_5m.var
    )
    bess_string_max_cell_voltage_v_5m = _voltage(
        Download.time_series.bess_string_max_cell_voltage_v_5m.var
    )

    # Current validation
    bess_string_current_amps_5m = _current(
        Download.time_series.bess_string_current_amps_5m.var
    )
