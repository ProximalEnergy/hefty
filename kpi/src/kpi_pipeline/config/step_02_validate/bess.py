import kpi_pipeline.services.calc as calc
import kpi_pipeline.services.process as process
from kpi_pipeline.base.field import Field
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate.utils import _capacity
from kpi_pipeline.services.schema import AddCalculationsSchema


def _soc(field: str) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=field),
            process=process.ProcessList(
                steps=[
                    process.VerifyWithinRangeProcess(min_value=0, max_value=1),
                    process.FilterToRangeProcess(
                        min_value=0.0, max_value=1.0, left_inclusive=False
                    ),
                ]
            ),
        ),
    )


def _soh(var: str) -> Field:
    return Field(
        calc.ProcessCalc(
            var=var,
            process=process.ProcessList(
                steps=[
                    process.VerifyWithinRangeProcess(min_value=0, max_value=1),
                    process.FilterToRangeProcess(min_value=0.2, max_value=1),
                ]
            ),
        )
    )


def _temperature(field: str) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=field),
            process=process.FilterToRangeProcess(min_value=1, max_value=150),
        ),
    )


def _voltage(field: str) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=field),
            process=process.FilterToRangeProcess(min_value=0, max_value=8),
        ),
    )


def _current(field: str) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=field),
            process=process.FilterToRangeProcess(min_value=-1000, max_value=1000),
        ),
    )


class ValidateBESS(AddCalculationsSchema):
    _update = True

    ##########################
    # Energy Capacity
    ##########################

    # project

    project_energy_capacity_kwh = _capacity(
        Download.project_attributes.project_energy_capacity_kwh.var
    )

    # pcs

    bess_pcs_energy_capacity_kwh = _capacity(
        Download.device_attributes.bess_pcs_energy_capacity_kwh.var
    )

    # pcs module

    bess_pcs_module_energy_capacity_kwh = _capacity(
        Download.device_attributes.bess_pcs_module_energy_capacity_kwh.var
    )

    # string

    bess_string_energy_capacity_kwh = _capacity(
        Download.device_attributes.bess_string_energy_capacity_kwh.var
    )

    #############################
    # Power Capacity
    #############################

    # project

    project_power_capacity_kw = _capacity(
        Download.project_attributes.project_power_capacity_kw.var
    )

    # circuit

    bess_mv_circuit_meter_power_capacity_kw = _capacity(
        Download.device_attributes.bess_mv_circuit_meter_power_capacity_kw.var
    )

    # pcs

    bess_pcs_power_capacity_kw = _capacity(
        Download.device_attributes.bess_pcs_power_capacity_kw.var
    )

    # pcs module

    bess_pcs_module_power_capacity_kw = _capacity(
        Download.device_attributes.bess_pcs_module_power_capacity_kw.var
    )

    # string

    bess_string_power_capacity_kw = _capacity(
        Download.device_attributes.bess_string_power_capacity_kw.var
    )

    #############################
    # Temperature
    #############################

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
        calc.FilterByCapacityCalc(
            data_var=Download.time_series.bess_pcs_power_kw_5m.var,
            capacity_var=Download.device_attributes.bess_pcs_power_capacity_kw.var,
            min_capacity_factor=-1.0,
            max_capacity_factor=1.0,
        )
    )

    bess_string_power_kw_5m = Field(
        calc.FilterByCapacityCalc(
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
