"""
power-based computations including C-rates and hours charging/discharging.
"""

import xarray as xr
from core.enumerations import DeviceType
from kpi.base.util import coord
from kpi.domain.bess import is_charging, is_discharging, is_idling
from kpi.domain.util import daily_mean_across_devices, date_local
from kpi.service.transform.method import Input, method_calc
from kpi.service.transform.schema import CalcSchema
from kpi.workflow.transform.bess.clean.workflow import TransformBessClean as Clean
from kpi.workflow.transform.bess.evaluate.evaluate import TransformBessEvaluate as Eval


class TransformBessSummarizePower(CalcSchema):
    # =======================================================
    # Project level
    # =======================================================

    # C_RATE (51)
    @method_calc
    def project_avg_c_rate_d(
        c_rate: xr.DataArray = Input(Eval.project_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return c_rate.groupby(date_local(date_local_5m)).mean()

    # BESS_PROJECT_AVERAGE_C_RATE_WHILE_CHARGING (75)
    @method_calc
    def project_avg_c_rate_while_charging_d(
        c_rate: xr.DataArray = Input(Eval.project_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            -c_rate.where(is_charging(c_rate)).groupby(date_local(date_local_5m)).mean()
        )

    # BESS_PROJECT_AVERAGE_C_RATE_WHILE_DISCHARGING (76)
    @method_calc
    def project_avg_c_rate_while_discharging_d(
        c_rate: xr.DataArray = Input(Eval.project_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            c_rate.where(is_discharging(c_rate))
            .groupby(date_local(date_local_5m))
            .mean()
        )

    # BESS_PROJECT_HOURS_CHARGING (83)
    @method_calc
    def project_hours_charging_d(
        c_rate: xr.DataArray = Input(Eval.project_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            xr.where(is_charging(c_rate), 5 / 60, 0)
            .groupby(date_local(date_local_5m))
            .sum()
        )

    # BESS_PROJECT_HOURS_DISCHARGING (84)
    @method_calc
    def project_hours_discharging_d(
        c_rate: xr.DataArray = Input(Eval.project_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            xr.where(is_discharging(c_rate), 5 / 60, 0)
            .groupby(date_local(date_local_5m))
            .sum()
        )

    # BESS_PROJECT_HOURS_IDLING (86)
    @method_calc
    def project_hours_idling_d(
        c_rate: xr.DataArray = Input(Eval.project_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            xr.where(is_idling(c_rate), 5 / 60, 0)
            .groupby(date_local(date_local_5m))
            .sum()
        )

    # =======================================================
    # BESS PCS
    # =======================================================

    # BESS_PCS_AVERAGE_C_RATE (77)

    @method_calc
    def pcs_avg_c_rate_d(
        c_rate: xr.DataArray = Input(Eval.pcs_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return c_rate.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_avg_pcs_c_rate_d(
        c_rate: xr.DataArray = Input(Eval.pcs_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=c_rate,
            device_type=DeviceType.BESS_PCS,
            date_local_5m=date_local_5m,
        )

    # BESS_PCS_AVERAGE_C_RATE_WHILE_CHARGING (78)
    @method_calc
    def pcs_avg_c_rate_while_charging_d(
        c_rate: xr.DataArray = Input(Eval.pcs_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            -c_rate.where(is_charging(c_rate)).groupby(date_local(date_local_5m)).mean()
        )

    @method_calc
    def project_avg_pcs_c_rate_while_charging_d(
        c_rate: xr.DataArray = Input(Eval.pcs_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=-c_rate.where(is_charging(c_rate)),
            device_type=DeviceType.BESS_PCS,
            date_local_5m=date_local_5m,
        )

    # BESS_PCS_AVERAGE_C_RATE_WHILE_DISCHARGING (79)
    @method_calc
    def pcs_avg_c_rate_while_discharging_d(
        c_rate: xr.DataArray = Input(Eval.pcs_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            c_rate.where(is_discharging(c_rate))
            .groupby(date_local(date_local_5m))
            .mean()
        )

    @method_calc
    def project_avg_pcs_c_rate_while_discharging_d(
        c_rate: xr.DataArray = Input(Eval.pcs_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=c_rate.where(is_discharging(c_rate)),
            device_type=DeviceType.BESS_PCS,
            date_local_5m=date_local_5m,
        )

    # BESS_PCS_HOURS_CHARGING (81)
    @method_calc
    def pcs_hours_charging_d(
        c_rate: xr.DataArray = Input(Eval.pcs_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            xr.where(is_charging(c_rate), 5 / 60, 0)
            .groupby(date_local(date_local_5m))
            .sum()
        )

    @method_calc
    def project_pcs_hours_charging_d(
        hours: xr.DataArray = Input(pcs_hours_charging_d.name),
    ) -> xr.DataArray:
        return hours.mean(dim=coord(DeviceType.BESS_PCS))

    # BESS_PCS_HOURS_DISCHARGING (82)
    @method_calc
    def pcs_hours_discharging_d(
        c_rate: xr.DataArray = Input(Eval.pcs_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            xr.where(is_discharging(c_rate), 5 / 60, 0)
            .groupby(date_local(date_local_5m))
            .sum()
        )

    @method_calc
    def project_pcs_hours_discharging_d(
        hours: xr.DataArray = Input(pcs_hours_discharging_d.name),
    ) -> xr.DataArray:
        return hours.mean(dim=coord(DeviceType.BESS_PCS))

    # BESS_PCS_HOURS_IDLING (85)
    @method_calc
    def pcs_hours_idling_d(
        c_rate: xr.DataArray = Input(Eval.pcs_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            xr.where(is_idling(c_rate), 5 / 60, 0)
            .groupby(date_local(date_local_5m))
            .sum()
        )

    @method_calc
    def project_pcs_hours_idling_d(
        hours: xr.DataArray = Input(pcs_hours_idling_d.name),
    ) -> xr.DataArray:
        return hours.mean(dim=coord(DeviceType.BESS_PCS))

    # BESS_PCS_AVG_REAL_AC_POWER_WHILE_CHARGING (89)
    @method_calc
    def pcs_avg_real_ac_power_while_charging_d(
        power: xr.DataArray = Input(Clean.pcs_power_kw_5m.name),
        energy_capacity: xr.DataArray = Input(Clean.pcs_energy_capacity_kwh.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            power.where(is_charging(power / energy_capacity))
            .groupby(date_local(date_local_5m))
            .mean()
        )

    @method_calc
    def project_avg_pcs_real_ac_power_while_charging_d(
        power: xr.DataArray = Input(Clean.pcs_power_kw_5m.name),
        energy_capacity: xr.DataArray = Input(Clean.pcs_energy_capacity_kwh.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=power.where(is_charging(power / energy_capacity)),
            device_type=DeviceType.BESS_PCS,
            date_local_5m=date_local_5m,
        )

    # BESS_PCS_AVG_REAL_AC_POWER_WHILE_DISCHARGING (90)
    @method_calc
    def pcs_avg_real_ac_power_while_discharging_d(
        power: xr.DataArray = Input(Clean.pcs_power_kw_5m.name),
        energy_capacity: xr.DataArray = Input(Clean.pcs_energy_capacity_kwh.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            power.where(is_discharging(power / energy_capacity))
            .groupby(date_local(date_local_5m))
            .mean()
        )

    @method_calc
    def project_avg_pcs_real_ac_power_while_discharging_d(
        power: xr.DataArray = Input(Clean.pcs_power_kw_5m.name),
        energy_capacity: xr.DataArray = Input(Clean.pcs_energy_capacity_kwh.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=power.where(is_discharging(power / energy_capacity)),
            device_type=DeviceType.BESS_PCS,
            date_local_5m=date_local_5m,
        )

    # =======================================================
    # BESS String
    # =======================================================

    # BESS_STRING_AVERAGE_C_RATE (56)
    @method_calc
    def string_avg_c_rate_d(
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return c_rate.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_avg_string_c_rate_d(
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=c_rate,
            device_type=DeviceType.BESS_STRING,
            date_local_5m=date_local_5m,
        )

    # BESS_STRING_AVG_C_RATE_WHILE_CHARGING (62)
    @method_calc
    def string_avg_c_rate_while_charging_d(
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            -c_rate.where(is_charging(c_rate)).groupby(date_local(date_local_5m)).mean()
        )

    @method_calc
    def project_avg_string_c_rate_while_charging_d(
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=-c_rate.where(is_charging(c_rate)),
            device_type=DeviceType.BESS_STRING,
            date_local_5m=date_local_5m,
        )

    # BESS_STRING_AVG_C_RATE_WHILE_DISCHARGING (63)
    @method_calc
    def string_avg_c_rate_while_discharging_d(
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (
            c_rate.where(is_discharging(c_rate))
            .groupby(date_local(date_local_5m))
            .mean()
        )

    @method_calc
    def project_avg_string_c_rate_while_discharging_d(
        c_rate: xr.DataArray = Input(Eval.string_c_rate_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=c_rate.where(is_discharging(c_rate)),
            device_type=DeviceType.BESS_STRING,
            date_local_5m=date_local_5m,
        )
