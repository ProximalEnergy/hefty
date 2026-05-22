"""
power-based computations including C-rates and hours charging/discharging.
"""

from core.enumerations import DeviceTypeEnum

from kpi.base.protocol import CalcProtocol
from kpi.domain.agg.across_devices import mean_across_devices
from kpi.domain.agg.other import daily_mean_across_devices
from kpi.domain.agg.resample import resample_mean
from kpi.domain.general import count_daily_hours_from_5m
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Constant, Grouper, Required
from kpi.op.transform.method import calc_field
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


class TransformBessSummarizePower(FieldRegistry[CalcProtocol]):
    # =======================================================
    # Project level
    # =======================================================

    # C_RATE (51)
    project_avg_c_rate_d = calc_field(resample_mean)(
        x=Required(Eval.project_c_rate_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    # BESS_PROJECT_AVERAGE_C_RATE_WHILE_CHARGING (75)
    project_avg_c_rate_while_charging_d = calc_field(resample_mean)(
        x=Required(Eval.project_c_rate_while_charging_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    # BESS_PROJECT_AVERAGE_C_RATE_WHILE_DISCHARGING (76)
    project_avg_c_rate_while_discharging_d = calc_field(resample_mean)(
        x=Required(Eval.project_c_rate_while_discharging_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    # BESS_PROJECT_HOURS_CHARGING (83)
    project_hours_charging_d = calc_field(count_daily_hours_from_5m)(
        bool_array_5m=Required(Eval.project_is_charging_5m),
        date_local_5m=Grouper(Eval.date_local_5m),
    )

    # BESS_PROJECT_HOURS_DISCHARGING (84)
    project_hours_discharging_d = calc_field(count_daily_hours_from_5m)(
        bool_array_5m=Required(Eval.project_is_discharging_5m),
        date_local_5m=Grouper(Eval.date_local_5m),
    )

    # BESS_PROJECT_HOURS_IDLING (86)
    project_hours_idling_d = calc_field(count_daily_hours_from_5m)(
        bool_array_5m=Required(Eval.project_is_idling_5m),
        date_local_5m=Grouper(Eval.date_local_5m),
    )

    # =======================================================
    # BESS PCS
    # =======================================================

    # BESS_PCS_AVERAGE_C_RATE (77)
    pcs_avg_c_rate_d = calc_field(resample_mean)(
        x=Required(Eval.pcs_c_rate_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    project_avg_pcs_c_rate_d = calc_field(daily_mean_across_devices)(
        value=Required(Eval.pcs_c_rate_5m),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
        date_local_5m=Grouper(Eval.date_local_5m),
    )

    # BESS_PCS_AVERAGE_C_RATE_WHILE_CHARGING (78)
    pcs_avg_c_rate_while_charging_d = calc_field(resample_mean)(
        x=Required(Eval.pcs_c_rate_while_charging_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    project_avg_pcs_c_rate_while_charging_d = calc_field(mean_across_devices)(
        x=Required(pcs_avg_c_rate_while_charging_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_AVERAGE_C_RATE_WHILE_DISCHARGING (79)
    pcs_avg_c_rate_while_discharging_d = calc_field(resample_mean)(
        x=Required(Eval.pcs_c_rate_while_discharging_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    project_avg_pcs_c_rate_while_discharging_d = calc_field(mean_across_devices)(
        x=Required(pcs_avg_c_rate_while_discharging_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_HOURS_CHARGING (81)
    pcs_hours_charging_d = calc_field(count_daily_hours_from_5m)(
        bool_array_5m=Required(Eval.pcs_is_charging_5m),
        date_local_5m=Grouper(Eval.date_local_5m),
    )

    project_pcs_hours_charging_d = calc_field(mean_across_devices)(
        x=Required(pcs_hours_charging_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_HOURS_DISCHARGING (82)
    pcs_hours_discharging_d = calc_field(count_daily_hours_from_5m)(
        bool_array_5m=Required(Eval.pcs_is_discharging_5m),
        date_local_5m=Grouper(Eval.date_local_5m),
    )

    project_pcs_hours_discharging_d = calc_field(mean_across_devices)(
        Required(pcs_hours_discharging_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_HOURS_IDLING (85)
    pcs_hours_idling_d = calc_field(count_daily_hours_from_5m)(
        bool_array_5m=Required(Eval.pcs_is_idling_5m),
        date_local_5m=Grouper(Eval.date_local_5m),
    )

    project_pcs_hours_idling_d = calc_field(mean_across_devices)(
        x=Required(pcs_hours_idling_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_AVG_REAL_AC_POWER_WHILE_CHARGING (89)
    pcs_avg_real_ac_power_while_charging_d = calc_field(resample_mean)(
        x=Required(Eval.pcs_power_while_charging_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    project_avg_pcs_real_ac_power_while_charging_d = calc_field(mean_across_devices)(
        x=Required(pcs_avg_real_ac_power_while_charging_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_AVG_REAL_AC_POWER_WHILE_DISCHARGING (90)
    pcs_avg_real_ac_power_while_discharging_d = calc_field(resample_mean)(
        x=Required(Eval.pcs_power_while_discharging_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    project_avg_pcs_real_ac_power_while_discharging_d = calc_field(mean_across_devices)(
        x=Required(pcs_avg_real_ac_power_while_discharging_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # =======================================================
    # BESS String
    # =======================================================

    # BESS_STRING_AVERAGE_C_RATE (56)
    string_avg_c_rate_d = calc_field(resample_mean)(
        x=Required(Eval.string_c_rate_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    project_avg_string_c_rate_d = calc_field(daily_mean_across_devices)(
        value=Required(Eval.string_c_rate_5m),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
        date_local_5m=Grouper(Eval.date_local_5m),
    )

    # BESS_STRING_AVG_C_RATE_WHILE_CHARGING (62)
    string_avg_c_rate_while_charging_d = calc_field(resample_mean)(
        x=Required(Eval.string_c_rate_while_charging_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    project_avg_string_c_rate_while_charging_d = calc_field(mean_across_devices)(
        x=Required(string_avg_c_rate_while_charging_d),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
    )

    # BESS_STRING_AVG_C_RATE_WHILE_DISCHARGING (63)
    string_avg_c_rate_while_discharging_d = calc_field(resample_mean)(
        x=Required(Eval.string_c_rate_while_discharging_5m),
        grouper=Grouper(Eval.date_local_5m),
    )

    project_avg_string_c_rate_while_discharging_d = calc_field(mean_across_devices)(
        x=Required(string_avg_c_rate_while_discharging_d),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
    )
