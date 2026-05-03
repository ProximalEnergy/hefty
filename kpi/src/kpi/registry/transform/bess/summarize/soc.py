"""
Includes soc related kpi computations including average SOC, resting SOC, and
SOC balance score, Depth of Discharge, and Cycle Count.
"""

import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.protocol import CalcProtocol
from kpi.base.util import coord
from kpi.domain.agg.across_devices import mean_across_devices
from kpi.domain.agg.other import daily_mean_across_devices
from kpi.domain.agg.resample import resample_mean
from kpi.domain.bess import cycle_count, depth_of_discharge, soc_balance_score
from kpi.domain.util import diff, rename
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Constant, Required
from kpi.op.transform.method import calc_field, method_calc
from kpi.registry.download.device.bess.hierarchy import DownloadDeviceBessHierarchy
from kpi.registry.transform.bess.clean.api import TransformBessClean as Clean
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


class TransformBessSummarizeSoc(FieldRegistry[CalcProtocol]):
    # blocks, modules (distinct from pcs modules), and enclosures not
    # implemented because they are being deprecated

    # =======================================================
    # Project level
    # =======================================================

    # PROJECT_AVERAGE_SOC_PERCENT (16)
    project_avg_soc_d = calc_field(resample_mean)(
        x=Required(Clean.project_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    # PROJECT_AVERAGE_DOD (47)
    project_avg_dod_d = calc_field(depth_of_discharge)(
        Required(project_avg_soc_d),
    )

    # PROJECT_RESTING_SOC_PERCENT (10)
    project_avg_resting_soc_d = calc_field(resample_mean)(
        x=Required(Eval.project_resting_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    # BESS_PROJECT_CHARGE_CYCLES (94)
    @method_calc(
        soc=Required(Clean.project_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_charge_cycles_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        cycle_delta = diff(soc)
        charging_periods = cycle_delta.where(cycle_delta >= 0)
        return charging_periods.groupby(rename(date_local_5m)).sum()

    # BESS_PROJECT_DISCHARGE_CYCLES (95)
    @method_calc(
        soc=Required(Clean.project_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_discharge_cycles_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        cycle_delta = diff(soc)
        discharging_periods = -cycle_delta.where(cycle_delta <= 0)
        return discharging_periods.groupby(rename(date_local_5m)).sum()

    # BESS_PROJECT_STRING_SOC_VARIANCE (118)
    @method_calc(
        soc=Required(Clean.string_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_string_soc_variance_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        min_data_coverage = 0.5
        var_5m = soc.var(dim=coord(DeviceTypeEnum.BESS_STRING))
        data_coverage = soc.notnull().mean(dim=coord(DeviceTypeEnum.BESS_STRING))
        var_5m = var_5m.where(data_coverage >= min_data_coverage)
        return var_5m.groupby(rename(date_local_5m)).mean()

    # PROJECT_STRING_SOC_BALANCE_SCORE (120)
    project_string_soc_balance_score_d = calc_field(soc_balance_score)(
        Required(project_string_soc_variance_d),
    )

    # PROJECT_CYCLE_COUNT (9)
    project_cycle_count_d = calc_field(cycle_count)(
        soc=Required(Clean.project_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    # =======================================================
    # PCS level
    # =======================================================

    # BESS_PCS_STRING_SOC_VARIANCE (119)
    @method_calc(
        soc=Required(Clean.string_soc_5m),
        string_to_pcs=Required(DownloadDeviceBessHierarchy.string_to_pcs),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def pcs_string_soc_variance_d(
        soc: xr.DataArray,
        string_to_pcs: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        min_data_coverage = 0.5
        device_grouper = string_to_pcs.rename(coord(DeviceTypeEnum.BESS_PCS))
        var_5m = soc.groupby(device_grouper).var()
        data_coverage = soc.notnull().groupby(device_grouper).mean()
        var_5m = var_5m.where(data_coverage >= min_data_coverage)
        daily = var_5m.groupby(rename(date_local_5m)).mean()
        daily_coverage = var_5m.notnull().groupby(rename(date_local_5m)).mean()
        daily = daily.where(daily_coverage >= min_data_coverage)
        return daily

    project_avg_pcs_string_soc_variance_d = calc_field(mean_across_devices)(
        x=Required(pcs_string_soc_variance_d),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
    )

    # BESS_PCS_STRING_SOC_BALANCE_SCORE (121)
    pcs_string_soc_balance_score_d = calc_field(soc_balance_score)(
        Required(pcs_string_soc_variance_d),
    )

    project_avg_pcs_string_soc_balance_score_d = calc_field(soc_balance_score)(
        Required(project_avg_pcs_string_soc_variance_d),
    )

    # =======================================================
    # Bank level
    # =======================================================

    # BESS_BANK_AVERAGE_SOC_PERCENT (24)
    bank_avg_soc_d = calc_field(resample_mean)(
        x=Required(Clean.bank_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_avg_bank_soc_d = calc_field(daily_mean_across_devices)(
        value=Required(Clean.bank_soc_5m),
        device_type=Constant(DeviceTypeEnum.BESS_BANK),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # BESS_BANK_RESTING_SOC_PERCENT (29)
    bank_avg_resting_soc_d = calc_field(resample_mean)(
        x=Required(Eval.bank_resting_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_avg_bank_resting_soc_d = calc_field(daily_mean_across_devices)(
        value=Required(Eval.bank_resting_soc_5m),
        device_type=Constant(DeviceTypeEnum.BESS_BANK),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # BESS_BANK_DEPTH_OF_DISCHARGE (26)
    bank_avg_dod_d = calc_field(depth_of_discharge)(
        Required(bank_avg_soc_d),
    )

    project_avg_bank_dod_d = calc_field(depth_of_discharge)(
        Required(project_avg_bank_soc_d),
    )

    # BESS_BANK_CYCLE_COUNT (31)
    bank_cycle_count_d = calc_field(cycle_count)(
        soc=Required(Clean.bank_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_avg_bank_cycle_count_d = calc_field(mean_across_devices)(
        x=Required(bank_cycle_count_d),
        device_type=Constant(DeviceTypeEnum.BESS_BANK),
    )

    # =======================================================
    # Block level
    # =======================================================

    # BESS_BLOCK_CYCLE_COUNT (11)
    block_cycle_count_d = calc_field(cycle_count)(
        soc=Required(Clean.block_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_avg_block_cycle_count_d = calc_field(mean_across_devices)(
        x=Required(block_cycle_count_d),
        device_type=Constant(DeviceTypeEnum.BESS_BLOCK),
    )

    # BESS_BLOCK_RESTING_SOC_PERCENT (12)
    block_avg_resting_soc_d = calc_field(resample_mean)(
        x=Required(Eval.block_resting_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_avg_block_resting_soc_d = calc_field(daily_mean_across_devices)(
        value=Required(Eval.block_resting_soc_5m),
        device_type=Constant(DeviceTypeEnum.BESS_BLOCK),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # BESS_BLOCK_AVERAGE_SOC_PERCENT (15)
    block_avg_soc_d = calc_field(resample_mean)(
        x=Required(Clean.block_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_avg_block_soc_d = calc_field(daily_mean_across_devices)(
        value=Required(Clean.block_soc_5m),
        device_type=Constant(DeviceTypeEnum.BESS_BLOCK),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # =======================================================
    # String level
    # =======================================================

    # BESS_STRING_AVERAGE_SOC_PERCENT (25)
    string_avg_soc_d = calc_field(resample_mean)(
        x=Required(Clean.string_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_avg_string_soc_d = calc_field(daily_mean_across_devices)(
        value=Required(Clean.string_soc_5m),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # BESS_STRING_RESTING_SOC_PERCENT (30)
    string_avg_resting_soc_d = calc_field(resample_mean)(
        x=Required(Eval.string_resting_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_avg_string_resting_soc_d = calc_field(daily_mean_across_devices)(
        value=Required(Eval.string_resting_soc_5m),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # BESS_STRING_DEPTH_OF_DISCHARGE (27)
    string_avg_dod_d = calc_field(depth_of_discharge)(
        Required(string_avg_soc_d),
    )

    project_avg_string_dod_d = calc_field(depth_of_discharge)(
        Required(project_avg_string_soc_d),
    )

    # BESS_STRING_CYCLE_COUNT (32)
    string_cycle_count_d = calc_field(cycle_count)(
        soc=Required(Clean.string_soc_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_avg_string_cycle_count_d = calc_field(mean_across_devices)(
        x=Required(string_cycle_count_d),
        device_type=Constant(DeviceTypeEnum.BESS_STRING),
    )
