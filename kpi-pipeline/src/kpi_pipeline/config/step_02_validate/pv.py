import kpi_pipeline.services.calc as calc
import kpi_pipeline.services.process as process
from kpi_pipeline.base.field import Field
from kpi_pipeline.config.helper_fields import _5min_to_daily
from kpi_pipeline.config.step_01_download import Download
from kpi_pipeline.config.step_02_validate.utils import _capacity
from kpi_pipeline.services.schema import AddCalculationsSchema


def _voltage_pv(field: str) -> Field:
    return Field(
        calc.CalcProcess(
            calc=calc.SelectCalc(var=field),
            process=process.FilterToRangeProcess(min_value=0, max_value=2000),
        ),
    )


class ValidatePV(AddCalculationsSchema):
    # Capacity validations
    project_power_capacity_dc_kw = _capacity(
        Download.project_attributes.project_power_capacity_dc_kw.var
    )
    pv_dc_combiner_power_capacity_dc_kw = _capacity(
        Download.device_attributes.pv_dc_combiner_power_capacity_dc_kw.var
    )
    pv_pcs_ac_capacity_kw = _capacity(
        Download.device_attributes.pv_pcs_ac_capacity_kw.var
    )
    pv_pcs_dc_capacity_kw = _capacity(
        Download.device_attributes.pv_pcs_dc_capacity_kw.var
    )

    met_station_irradiance_poa_w_m2_5m = Field(
        calc.ProcessCalc(
            var=Download.time_series.met_station_irradiance_poa_w_m2_5m.var,
            process=process.ProcessList(
                [
                    process.RemoveFlatLiningProcess(
                        time_combiner_model=_5min_to_daily(),
                    ),
                    process.ClampProcess(min_value=0),
                ]
            ),
        )
    )

    # power validation

    project_active_power_meter_kw_5m = Field(
        calc.FilterByCapacityCalc(
            data_var=Download.time_series.project_active_power_meter_kw_5m.var,
            capacity_var=Download.project_attributes.project_power_capacity_dc_kw.var,
            min_capacity_factor=-0.1,
            max_capacity_factor=1.0,
        )
    )

    pv_pcs_active_power_ac_kw_5m = Field(
        calc.FilterByCapacityCalc(
            data_var=Download.time_series.pv_pcs_active_power_ac_kw_5m.var,
            capacity_var=Download.device_attributes.pv_pcs_ac_capacity_kw.var,
            min_capacity_factor=0.0,
            max_capacity_factor=1.0,
        )
    )

    # power setpoint validation
    project_power_setpoint_kw_5m = Field(
        calc.FilterByCapacityCalc(
            data_var=Download.time_series.project_power_setpoint_kw_5m.var,
            capacity_var=Download.project_attributes.project_power_capacity_dc_kw.var,
            min_capacity_factor=0.0,
            max_capacity_factor=1.0,
        )
    )

    pv_pcs_active_power_setpoint_kw_5m = Field(
        calc.FilterByCapacityCalc(
            data_var=Download.time_series.pv_pcs_active_power_setpoint_kw_5m.var,
            capacity_var=Download.device_attributes.pv_pcs_ac_capacity_kw.var,
            min_capacity_factor=0.0,
            max_capacity_factor=1.0,
        )
    )

    # tracker validation
    tracker_row_position_deg_5m = Field(
        calc.ProcessCalc(
            var=Download.time_series.tracker_row_position_deg_5m.var,
            process=process.FilterToRangeProcess(
                min_value=-90,
                max_value=90,
            ),
        )
    )
    tracker_row_setpoint_deg_5m = Field(
        calc.ProcessCalc(
            var=Download.time_series.tracker_row_setpoint_deg_5m.var,
            process=process.FilterToRangeProcess(
                min_value=-90,
                max_value=90,
            ),
        )
    )

    # voltage validation
    pv_pcs_voltage_v_5m = _voltage_pv(Download.time_series.pv_pcs_voltage_v_5m.var)
    pv_pcs_module_voltage_v_5m = _voltage_pv(
        Download.time_series.pv_pcs_module_voltage_v_5m.var
    )
