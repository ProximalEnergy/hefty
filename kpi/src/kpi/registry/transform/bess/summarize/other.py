"""
SoH, Temperature, voltage, and other miscellaneous kpis.
"""

import xarray as xr
from core.enumerations import DeviceTypeEnum

from kpi.base.enumeration import TimeCoord
from kpi.base.protocol import CalcProtocol
from kpi.domain.agg.across_devices import (
    max_across_devices,
    mean_across_devices,
    min_across_devices,
)
from kpi.domain.agg.other import daily_mean_across_devices
from kpi.domain.agg.resample import (
    resample_first,
    resample_max,
    resample_mean,
    resample_min,
)
from kpi.domain.bess import is_charging, is_discharging
from kpi.domain.util import diff
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Constant, grouper, required
from kpi.op.transform.method import calc_field
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


def string_avg_current_while_charging_amps_d(
    *, current: xr.DataArray, c_rate: xr.DataArray, date_local_5m: xr.DataArray
) -> xr.DataArray:
    """Daily mean string current during charging.

    Args:
        current: String current at 5-minute resolution.
        c_rate: String C-rate at 5-minute resolution.
        date_local_5m: Local date grouper aligned to the time dimension.

    Returns:
        Daily mean current while charging.
    """
    return current.where(is_charging(c_rate)).groupby(date_local_5m).mean()


def project_avg_string_current_while_charging_amps_d(
    *, current: xr.DataArray, c_rate: xr.DataArray, date_local_5m: xr.DataArray
) -> xr.DataArray:
    """Project daily mean string current while charging.

    Args:
        current: String current at 5-minute resolution.
        c_rate: String C-rate at 5-minute resolution.
        date_local_5m: Local date grouper aligned to the time dimension.

    Returns:
        Daily mean across strings of charging current.
    """
    return daily_mean_across_devices(
        value=current.where(is_charging(c_rate)),
        device_type=DeviceTypeEnum.BESS_STRING,
        date_local_5m=date_local_5m,
    )


def string_avg_current_while_discharging_amps_d(
    *, current: xr.DataArray, c_rate: xr.DataArray, date_local_5m: xr.DataArray
) -> xr.DataArray:
    """Daily mean string current during discharging.

    Args:
        current: String current at 5-minute resolution.
        c_rate: String C-rate at 5-minute resolution.
        date_local_5m: Local date grouper aligned to the time dimension.

    Returns:
        Daily mean current while discharging.
    """
    return current.where(is_discharging(c_rate)).groupby(date_local_5m).mean()


def project_avg_string_current_while_discharging_amps_d(
    *, current: xr.DataArray, c_rate: xr.DataArray, date_local_5m: xr.DataArray
) -> xr.DataArray:
    """Project daily mean string current while discharging.

    Args:
        current: String current at 5-minute resolution.
        c_rate: String C-rate at 5-minute resolution.
        date_local_5m: Local date grouper aligned to the time dimension.

    Returns:
        Daily mean across strings of discharging current.
    """
    return daily_mean_across_devices(
        value=current.where(is_discharging(c_rate)),
        device_type=DeviceTypeEnum.BESS_STRING,
        date_local_5m=date_local_5m,
    )


class TransformBessSummarizeOther(FieldRegistry[CalcProtocol]):
    # =======================================================
    # SoH
    # =======================================================

    project_soh_d = calc_field(resample_first)(
        required(Eval.project_soh_5m), grouper=grouper(Eval.date_local_5m)
    )

    # BESS_BANK_SOH (53)
    bank_soh_d = calc_field(resample_first)(
        required(Clean.bank_soh_5m), grouper=grouper(Eval.date_local_5m)
    )

    project_bank_soh_d = calc_field(mean_across_devices)(
        required(bank_soh_d), device_type=Constant(value=DeviceTypeEnum.BESS_BANK)
    )

    # BESS_STRING_SOH (54)
    string_soh_d = calc_field(resample_first)(
        required(Clean.string_soh_5m), grouper=grouper(Eval.date_local_5m)
    )

    project_string_soh_d = calc_field(mean_across_devices)(
        required(string_soh_d), device_type=Constant(value=DeviceTypeEnum.BESS_STRING)
    )

    # =======================================================
    # Degradation
    # =======================================================

    # BESS_STRING_DEGRADATION (80)
    string_degradation_d = calc_field(diff)(
        required(string_soh_d), time_dim=Constant(value=TimeCoord.DATE_LOCAL)
    )

    project_string_degradation_d = calc_field(diff)(
        required(project_string_soh_d), time_dim=Constant(value=TimeCoord.DATE_LOCAL)
    )

    # =======================================================
    # Temperature
    # =======================================================

    # BESS_STRING_MIN_MODULE_TEMP (59)
    string_min_module_temp_d = calc_field(resample_min)(
        x=required(Clean.string_min_module_temp_c_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_string_min_module_temp_d = calc_field(min_across_devices)(
        x=required(string_min_module_temp_d),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_MAX_MODULE_TEMP (60)
    string_max_module_temp_d = calc_field(resample_max)(
        x=required(Clean.string_max_module_temp_c_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_string_max_module_temp_d = calc_field(max_across_devices)(
        x=required(string_max_module_temp_d),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_AVG_MODULE_TEMP (61)
    string_avg_module_temp_d = calc_field(resample_mean)(
        x=required(Clean.string_avg_module_temp_c_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_string_avg_module_temp_d = calc_field(daily_mean_across_devices)(
        value=required(Clean.string_avg_module_temp_c_5m),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    # BESS_STRING_AVG_CELL_TEMPERATURE (72)
    string_avg_cell_temperature_d = calc_field(resample_mean)(
        x=required(Clean.string_avg_cell_temp_c_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_string_avg_cell_temperature_d = calc_field(daily_mean_across_devices)(
        value=required(Clean.string_avg_cell_temp_c_5m),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    # BESS_STRING_MAX_CELL_TEMPERATURE (73)
    string_max_cell_temperature_d = calc_field(resample_max)(
        x=required(Clean.string_max_cell_temp_c_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_max_cell_temperature_d = calc_field(max_across_devices)(
        x=required(string_max_cell_temperature_d),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_MIN_CELL_TEMPERATURE (74)
    string_min_cell_temperature_d = calc_field(resample_min)(
        x=required(Clean.string_min_cell_temp_c_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_min_cell_temperature_d = calc_field(min_across_devices)(
        x=required(string_min_cell_temperature_d),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
    )

    # =======================================================
    # Voltage
    # =======================================================

    # BESS_STRING_MIN_CELL_VOLTAGE (64)
    string_min_cell_voltage_d = calc_field(resample_min)(
        x=required(Clean.string_min_cell_voltage_v_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_min_cell_voltage_d = calc_field(min_across_devices)(
        x=required(string_min_cell_voltage_d),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_AVG_CELL_VOLTAGE (65)
    string_avg_cell_voltage_d = calc_field(resample_mean)(
        x=required(Clean.string_avg_cell_voltage_v_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_avg_cell_voltage_d = calc_field(daily_mean_across_devices)(
        value=required(Clean.string_avg_cell_voltage_v_5m),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    # BESS_STRING_MAX_CELL_VOLTAGE (66)
    string_max_cell_voltage_d = calc_field(resample_max)(
        x=required(Clean.string_max_cell_voltage_v_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_max_cell_voltage_d = calc_field(max_across_devices)(
        x=required(string_max_cell_voltage_d),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
    )

    # =======================================================
    # Current
    # =======================================================

    # BESS_STRING_AVG_CURRENT (67)
    string_avg_current_amps_d = calc_field(resample_mean)(
        x=required(Clean.string_current_amps_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_avg_string_current_amps_d = calc_field(daily_mean_across_devices)(
        value=required(Clean.string_current_amps_5m),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    # BESS_STRING_MAX_CURRENT (68)
    string_max_current_amps_d = calc_field(resample_max)(
        x=required(Clean.string_current_amps_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_max_string_current_amps_d = calc_field(max_across_devices)(
        x=required(string_max_current_amps_d),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_MIN_CURRENT (69)
    string_min_current_amps_d = calc_field(resample_min)(
        x=required(Clean.string_current_amps_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_min_string_current_amps_d = calc_field(min_across_devices)(
        x=required(string_min_current_amps_d),
        device_type=Constant(value=DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_AVG_CURRENT_WHILE_CHARGING (70)
    string_avg_current_while_charging_amps_d = calc_field(
        string_avg_current_while_charging_amps_d
    )(
        current=required(Clean.string_current_amps_5m),
        c_rate=required(Eval.string_c_rate_5m),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    project_avg_string_current_while_charging_amps_d = calc_field(
        project_avg_string_current_while_charging_amps_d
    )(
        current=required(Clean.string_current_amps_5m),
        c_rate=required(Eval.string_c_rate_5m),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    # BESS_STRING_AVG_CURRENT_WHILE_DISCHARGING (71)
    string_avg_current_while_discharging_amps_d = calc_field(
        string_avg_current_while_discharging_amps_d
    )(
        current=required(Clean.string_current_amps_5m),
        c_rate=required(Eval.string_c_rate_5m),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    project_avg_string_current_while_discharging_amps_d = calc_field(
        project_avg_string_current_while_discharging_amps_d
    )(
        current=required(Clean.string_current_amps_5m),
        c_rate=required(Eval.string_c_rate_5m),
        date_local_5m=grouper(Eval.date_local_5m),
    )
