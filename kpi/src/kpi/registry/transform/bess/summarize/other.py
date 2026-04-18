"""
SoH, Temperature, voltage, and other miscellaneous kpis.
"""

import xarray as xr
from core.enumerations import DeviceType
from kpi.base.enumeration import TimeCoords
from kpi.base.protocol import CalcProtocol
from kpi.base.util import coord
from kpi.domain.bess import diff, is_charging, is_discharging
from kpi.domain.util import daily_mean_across_devices, date_local
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.method import Input, method_calc
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


class TransformBessSummarizeOther(FieldRegistry[CalcProtocol]):
    # =======================================================
    # SoH
    # =======================================================

    # BESS_BANK_SOH (53)
    @method_calc
    def bank_soh_d(
        soh: xr.DataArray = Input(Clean.bank_soh_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return soh.groupby(date_local(date_local_5m)).first()

    @method_calc
    def project_bank_soh_d(
        soh: xr.DataArray = Input(bank_soh_d),
    ) -> xr.DataArray:
        return soh.mean(dim=coord(DeviceType.BESS_BANK))

    # BESS_STRING_SOH (54)
    @method_calc
    def string_soh_d(
        soh: xr.DataArray = Input(Clean.string_soh_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return soh.groupby(date_local(date_local_5m)).first()

    @method_calc
    def project_string_soh_d(
        soh: xr.DataArray = Input(string_soh_d),
    ) -> xr.DataArray:
        return soh.mean(dim=coord(DeviceType.BESS_STRING))

    # =======================================================
    # Degradation
    # =======================================================

    # BESS_STRING_DEGRADATION (80)
    @method_calc
    def string_degradation_d(
        soh: xr.DataArray = Input(string_soh_d),
    ) -> xr.DataArray:
        return diff(soh, time_dim=TimeCoords.DATE_LOCAL)

    @method_calc
    def project_string_degradation_d(
        soh: xr.DataArray = Input(project_string_soh_d),
    ) -> xr.DataArray:
        return diff(soh, time_dim=TimeCoords.DATE_LOCAL)

    # =======================================================
    # Temperature
    # =======================================================

    # BESS_STRING_MIN_MODULE_TEMP (59)
    @method_calc
    def string_min_module_temp_d(
        temp: xr.DataArray = Input(Clean.string_min_module_temp_c_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return temp.groupby(date_local(date_local_5m)).min()

    @method_calc
    def project_string_min_module_temp_d(
        temp: xr.DataArray = Input(string_min_module_temp_d),
    ) -> xr.DataArray:
        return temp.min(dim=coord(DeviceType.BESS_STRING))

    # BESS_STRING_MAX_MODULE_TEMP (60)
    @method_calc
    def string_max_module_temp_d(
        temp: xr.DataArray = Input(Clean.string_max_module_temp_c_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return temp.groupby(date_local(date_local_5m)).max()

    @method_calc
    def project_string_max_module_temp_d(
        temp: xr.DataArray = Input(string_max_module_temp_d),
    ) -> xr.DataArray:
        return temp.max(dim=coord(DeviceType.BESS_STRING))

    # BESS_STRING_AVG_MODULE_TEMP (61)
    @method_calc
    def string_avg_module_temp_d(
        temp: xr.DataArray = Input(Clean.string_avg_module_temp_c_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return temp.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_string_avg_module_temp_d(
        temp: xr.DataArray = Input(Clean.string_avg_module_temp_c_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=temp,
            device_type=DeviceType.BESS_STRING,
            date_local_5m=date_local_5m,
        )

    # BESS_STRING_AVG_CELL_TEMPERATURE (72)
    @method_calc
    def string_avg_cell_temperature_d(
        temp: xr.DataArray = Input(Clean.string_avg_cell_temp_c_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return temp.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_string_avg_cell_temperature_d(
        temp: xr.DataArray = Input(Clean.string_avg_cell_temp_c_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=temp,
            device_type=DeviceType.BESS_STRING,
            date_local_5m=date_local_5m,
        )

    # BESS_STRING_MAX_CELL_TEMPERATURE (73)
    @method_calc
    def string_max_cell_temperature_d(
        temp: xr.DataArray = Input(Clean.string_max_cell_temp_c_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return temp.groupby(date_local(date_local_5m)).max()

    @method_calc
    def project_max_cell_temperature_d(
        temp: xr.DataArray = Input(string_max_cell_temperature_d),
    ) -> xr.DataArray:
        return temp.max(dim=coord(DeviceType.BESS_STRING))

    # BESS_STRING_MIN_CELL_TEMPERATURE (74)
    @method_calc
    def string_min_cell_temperature_d(
        temp: xr.DataArray = Input(Clean.string_min_cell_temp_c_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return temp.groupby(date_local(date_local_5m)).min()

    @method_calc
    def project_min_cell_temperature_d(
        temp: xr.DataArray = Input(string_min_cell_temperature_d),
    ) -> xr.DataArray:
        return temp.min(dim=coord(DeviceType.BESS_STRING))

    # =======================================================
    # Voltage
    # =======================================================

    # BESS_STRING_MIN_CELL_VOLTAGE (64)
    @method_calc
    def string_min_cell_voltage_d(
        voltage: xr.DataArray = Input(Clean.string_min_cell_voltage_v_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return voltage.groupby(date_local(date_local_5m)).min()

    @method_calc
    def project_min_cell_voltage_d(
        voltage: xr.DataArray = Input(string_min_cell_voltage_d),
    ) -> xr.DataArray:
        return voltage.min(dim=coord(DeviceType.BESS_STRING))

    # BESS_STRING_AVG_CELL_VOLTAGE (65)
    @method_calc
    def string_avg_cell_voltage_d(
        voltage: xr.DataArray = Input(Clean.string_avg_cell_voltage_v_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return voltage.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_avg_cell_voltage_d(
        voltage: xr.DataArray = Input(Clean.string_avg_cell_voltage_v_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=voltage,
            device_type=DeviceType.BESS_STRING,
            date_local_5m=date_local_5m,
        )

    # BESS_STRING_MAX_CELL_VOLTAGE (66)
    @method_calc
    def string_max_cell_voltage_d(
        voltage: xr.DataArray = Input(Clean.string_max_cell_voltage_v_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return voltage.groupby(date_local(date_local_5m)).max()

    @method_calc
    def project_max_cell_voltage_d(
        voltage: xr.DataArray = Input(string_max_cell_voltage_d),
    ) -> xr.DataArray:
        return voltage.max(dim=coord(DeviceType.BESS_STRING))

    # =======================================================
    # Current
    # =======================================================

    # BESS_STRING_AVG_CURRENT (67)
    @method_calc
    def string_avg_current_amps_d(
        current: xr.DataArray = Input(Clean.string_current_amps_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return current.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_avg_string_current_amps_d(
        current: xr.DataArray = Input(Clean.string_current_amps_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=current,
            device_type=DeviceType.BESS_STRING,
            date_local_5m=date_local_5m,
        )

    # BESS_STRING_MAX_CURRENT (68)
    @method_calc
    def string_max_current_amps_d(
        current: xr.DataArray = Input(Clean.string_current_amps_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return current.groupby(date_local(date_local_5m)).max()

    @method_calc
    def project_max_string_current_amps_d(
        current: xr.DataArray = Input(string_max_current_amps_d),
    ) -> xr.DataArray:
        return current.max(dim=coord(DeviceType.BESS_STRING))

    # BESS_STRING_MIN_CURRENT (69)
    @method_calc
    def string_min_current_amps_d(
        current: xr.DataArray = Input(Clean.string_current_amps_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return current.groupby(date_local(date_local_5m)).min()

    @method_calc
    def project_min_string_current_amps_d(
        current: xr.DataArray = Input(string_min_current_amps_d),
    ) -> xr.DataArray:
        return current.min(dim=coord(DeviceType.BESS_STRING))

    # BESS_STRING_AVG_CURRENT_WHILE_CHARGING (70)
    @method_calc
    def string_avg_current_while_charging_amps_d(
        current: xr.DataArray = Input(Clean.string_current_amps_5m),
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return (
            current.where(is_charging(c_rate)).groupby(date_local(date_local_5m)).mean()
        )

    @method_calc
    def project_avg_string_current_while_charging_amps_d(
        current: xr.DataArray = Input(Clean.string_current_amps_5m),
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=current.where(is_charging(c_rate)),
            device_type=DeviceType.BESS_STRING,
            date_local_5m=date_local_5m,
        )

    # BESS_STRING_AVG_CURRENT_WHILE_DISCHARGING (71)
    @method_calc
    def string_avg_current_while_discharging_amps_d(
        current: xr.DataArray = Input(Clean.string_current_amps_5m),
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return (
            current.where(is_discharging(c_rate))
            .groupby(date_local(date_local_5m))
            .mean()
        )

    @method_calc
    def project_avg_string_current_while_discharging_amps_d(
        current: xr.DataArray = Input(Clean.string_current_amps_5m),
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=current.where(is_discharging(c_rate)),
            device_type=DeviceType.BESS_STRING,
            date_local_5m=date_local_5m,
        )
