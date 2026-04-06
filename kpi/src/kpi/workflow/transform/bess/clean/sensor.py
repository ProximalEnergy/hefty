import xarray as xr
from kpi.domain.bess import clean_cell_voltage, clean_soc, clean_soh, clean_temperature
from kpi.domain.util import filter_mask
from kpi.service.transform.method import Input, method_calc
from kpi.service.transform.schema import CalcSchema
from kpi.service.transform.unary import unary_field
from kpi.workflow.download.sensor.bess import DownloadSensorBess as Sensor
from kpi.workflow.transform.bess.clean.device_attribute import (
    TransformBessCleanDeviceAttribute as Device,
)
from kpi.workflow.transform.bess.clean.project_attribute import (
    TransformBessCleanProjectAttribute as Project,
)


class TransformBessCleanSensor(CalcSchema):
    # =======================================================
    # Energy
    # =======================================================

    # project level

    # project_total_energy_charged_raw_kwh_5m

    # project_total_energy_discharged_raw_kwh_5m

    # project_total_aux_energy_kwh_5m

    # mv circuit level

    # circuit_total_energy_charged_kwh_5m

    # circuit_total_energy_discharged_kwh_5m

    # pcs level

    # pcs_total_energy_charged_kwh_5m

    # pcs_total_energy_discharged_kwh_5m

    # pcs module level

    # pcs_module_total_energy_discharged_kwh_5m

    # pcs_module_total_energy_charged_kwh_5m

    # string level

    # string_total_energy_charged_kwh_5m

    # string_total_energy_discharged_kwh_5m

    # =======================================================
    # Power
    # =======================================================

    # project level

    @method_calc
    def bess_project_power_kw_5m(
        power: xr.DataArray = Input(Sensor.project_power_raw_kw_5m),
        capacity: xr.DataArray = Input(Project.project_power_capacity_kw),
    ) -> xr.DataArray:
        return power.where(
            filter_mask(filter_by=power / capacity, min_value=-1, max_value=1)
        )

    # pcs level

    @method_calc
    def pcs_power_kw_5m(
        power: xr.DataArray = Input(Sensor.pcs_power_raw_kw_5m),
        capacity: xr.DataArray = Input(Device.pcs_power_capacity_kw),
    ) -> xr.DataArray:
        return power.where(
            filter_mask(filter_by=power / capacity, min_value=-1, max_value=1)
        )

    # string

    @method_calc
    def string_power_kw_5m(
        power: xr.DataArray = Input(Sensor.string_power_raw_kw_5m),
        capacity: xr.DataArray = Input(Device.string_power_capacity_kw),
    ) -> xr.DataArray:
        return power.where(
            filter_mask(filter_by=power / capacity, min_value=-1, max_value=1)
        )

    # =======================================================
    # SOC
    # =======================================================

    project_soc_5m = unary_field(
        clean_soc,
        field=Sensor.project_soc_raw_5m,
    )

    bank_soc_5m = unary_field(
        clean_soc,
        field=Sensor.bank_soc_raw_5m,
    )

    block_soc_5m = unary_field(
        clean_soc,
        field=Sensor.block_soc_raw_5m,
    )

    string_soc_5m = unary_field(
        clean_soc,
        field=Sensor.string_soc_raw_5m,
    )

    # =======================================================
    # SOH
    # =======================================================

    bank_soh_5m = unary_field(
        clean_soh,
        field=Sensor.bank_soh_raw_5m,
    )

    string_soh_5m = unary_field(
        clean_soh,
        field=Sensor.string_soh_raw_5m,
    )

    # =======================================================
    # Current
    # =======================================================

    @method_calc
    def string_current_amps_5m(
        current: xr.DataArray = Input(Sensor.string_current_raw_amps_5m),
    ) -> xr.DataArray:
        return current.where(
            filter_mask(filter_by=current, min_value=-1000, max_value=1000)
        )

    # =======================================================
    # Temperature
    # =======================================================

    string_avg_cell_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_avg_cell_temp_raw_c_5m,
    )

    string_min_cell_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_min_cell_temp_raw_c_5m,
    )

    string_max_cell_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_max_cell_temp_raw_c_5m,
    )

    string_min_module_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_min_module_temp_raw_c_5m,
    )

    string_max_module_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_max_module_temp_raw_c_5m,
    )

    string_avg_module_temp_c_5m = unary_field(
        clean_temperature,
        field=Sensor.string_avg_module_temp_raw_c_5m,
    )

    # =======================================================
    # Voltage
    # =======================================================

    string_avg_cell_voltage_v_5m = unary_field(
        clean_cell_voltage,
        field=Sensor.string_avg_cell_voltage_raw_v_5m,
    )

    string_min_cell_voltage_v_5m = unary_field(
        clean_cell_voltage,
        field=Sensor.string_min_cell_voltage_raw_v_5m,
    )

    string_max_cell_voltage_v_5m = unary_field(
        clean_cell_voltage,
        field=Sensor.string_max_cell_voltage_raw_v_5m,
    )
