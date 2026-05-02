"""
Includes soc related kpi computations including average SOC, resting SOC, and
SOC balance score, Depth of Discharge, and Cycle Count.
"""

import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.protocol import CalcProtocol
from kpi.base.util import coord
from kpi.domain.bess import cycle_count, soc_balance_score
from kpi.domain.util import daily_mean_across_devices, date_local, diff
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.input import Required
from kpi.op.transform.method import method_calc
from kpi.op.transform.unary import unary_field
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
    @method_calc(
        soc=Required(Clean.project_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_avg_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return soc.groupby(date_local(date_local_5m)).mean()

    # PROJECT_AVERAGE_DOD (47)
    @method_calc(
        soc=Required(project_avg_soc_d),
    )
    def project_avg_dod_d(
        soc: xr.DataArray,
    ) -> xr.DataArray:
        return 1 - soc

    # PROJECT_RESTING_SOC_PERCENT (10)
    @method_calc(
        soc=Required(Eval.project_resting_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_avg_resting_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return soc.groupby(date_local(date_local_5m)).mean()

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
        return charging_periods.groupby(date_local(date_local_5m)).sum()

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
        return discharging_periods.groupby(date_local(date_local_5m)).sum()

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
        return var_5m.groupby(date_local(date_local_5m)).mean()

    # PROJECT_STRING_SOC_BALANCE_SCORE (120)
    project_string_soc_balance_score_d = unary_field(
        soc_balance_score,
        field=project_string_soc_variance_d,
    )

    # PROJECT_CYCLE_COUNT (9)
    @method_calc(
        soc=Required(Clean.project_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_cycle_count_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return cycle_count(soc=soc, grouper=date_local(date_local_5m))

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
        daily = var_5m.groupby(date_local(date_local_5m)).mean()
        daily_coverage = var_5m.notnull().groupby(date_local(date_local_5m)).mean()
        daily = daily.where(daily_coverage >= min_data_coverage)
        return daily

    @method_calc(
        pcs_string_soc_var=Required(pcs_string_soc_variance_d),
    )
    def project_avg_pcs_string_soc_variance_d(
        pcs_string_soc_var: xr.DataArray,
    ) -> xr.DataArray:
        return pcs_string_soc_var.mean(dim=coord(DeviceTypeEnum.BESS_PCS))

    # BESS_PCS_STRING_SOC_BALANCE_SCORE (121)
    pcs_string_soc_balance_score_d = unary_field(
        soc_balance_score,
        field=pcs_string_soc_variance_d,
    )

    project_avg_pcs_string_soc_balance_score_d = unary_field(
        soc_balance_score,
        field=project_avg_pcs_string_soc_variance_d,
    )

    # =======================================================
    # Bank level
    # =======================================================

    # BESS_BANK_AVERAGE_SOC_PERCENT (24)
    @method_calc(
        soc=Required(Clean.bank_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def bank_avg_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return soc.groupby(date_local(date_local_5m)).mean()

    @method_calc(
        soc=Required(Clean.bank_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_avg_bank_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=soc, device_type=DeviceTypeEnum.BESS_BANK, date_local_5m=date_local_5m
        )

    # BESS_BANK_RESTING_SOC_PERCENT (29)
    @method_calc(
        soc=Required(Eval.bank_resting_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def bank_avg_resting_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return soc.groupby(date_local(date_local_5m)).mean()

    @method_calc(
        soc=Required(Eval.bank_resting_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_avg_bank_resting_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=soc, device_type=DeviceTypeEnum.BESS_BANK, date_local_5m=date_local_5m
        )

    # BESS_BANK_DEPTH_OF_DISCHARGE (26)
    @method_calc(
        soc=Required(bank_avg_soc_d),
    )
    def bank_avg_dod_d(
        soc: xr.DataArray,
    ):
        return 1 - soc

    @method_calc(
        soc=Required(project_avg_bank_soc_d),
    )
    def project_avg_bank_dod_d(
        soc: xr.DataArray,
    ):
        return 1 - soc

    # BESS_BANK_CYCLE_COUNT (31)
    @method_calc(
        soc=Required(Clean.bank_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def bank_cycle_count_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return cycle_count(soc=soc, grouper=date_local(date_local_5m))

    @method_calc(
        cycle_count=Required(bank_cycle_count_d),
    )
    def project_avg_bank_cycle_count_d(
        cycle_count: xr.DataArray,
    ):
        return cycle_count.mean(dim=coord(DeviceTypeEnum.BESS_BANK))

    # =======================================================
    # Block level
    # =======================================================

    # BESS_BLOCK_CYCLE_COUNT (11)
    @method_calc(
        soc=Required(Clean.block_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def block_cycle_count_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return cycle_count(soc=soc, grouper=date_local(date_local_5m))

    @method_calc(
        cycle_count=Required(block_cycle_count_d),
    )
    def project_avg_block_cycle_count_d(
        cycle_count: xr.DataArray,
    ):
        return cycle_count.mean(dim=coord(DeviceTypeEnum.BESS_BLOCK))

    # BESS_BLOCK_RESTING_SOC_PERCENT (12)
    @method_calc(
        soc=Required(Eval.block_resting_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def block_avg_resting_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return soc.groupby(date_local(date_local_5m)).mean()

    @method_calc(
        soc=Required(Eval.block_resting_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_avg_block_resting_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=soc, device_type=DeviceTypeEnum.BESS_BLOCK, date_local_5m=date_local_5m
        )

    # BESS_BLOCK_AVERAGE_SOC_PERCENT (15)
    @method_calc(
        soc=Required(Clean.block_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def block_avg_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return soc.groupby(date_local(date_local_5m)).mean()

    @method_calc(
        soc=Required(Clean.block_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_avg_block_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=soc, device_type=DeviceTypeEnum.BESS_BLOCK, date_local_5m=date_local_5m
        )

    # =======================================================
    # String level
    # =======================================================

    # BESS_STRING_AVERAGE_SOC_PERCENT (25)
    @method_calc(
        soc=Required(Clean.string_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def string_avg_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return soc.groupby(date_local(date_local_5m)).mean()

    @method_calc(
        soc=Required(Clean.string_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_avg_string_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=soc, device_type=DeviceTypeEnum.BESS_STRING, date_local_5m=date_local_5m
        )

    # BESS_STRING_RESTING_SOC_PERCENT (30)
    @method_calc(
        soc=Required(Eval.string_resting_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def string_avg_resting_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return soc.groupby(date_local(date_local_5m)).mean()

    @method_calc(
        soc=Required(Eval.string_resting_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_avg_string_resting_soc_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=soc, device_type=DeviceTypeEnum.BESS_STRING, date_local_5m=date_local_5m
        )

    # BESS_STRING_DEPTH_OF_DISCHARGE (27)
    @method_calc(
        soc=Required(string_avg_soc_d),
    )
    def string_avg_dod_d(
        soc: xr.DataArray,
    ):
        return 1 - soc

    @method_calc(
        soc=Required(project_avg_string_soc_d),
    )
    def project_avg_string_dod_d(
        soc: xr.DataArray,
    ):
        return 1 - soc

    # BESS_STRING_CYCLE_COUNT (32)
    @method_calc(
        soc=Required(Clean.string_soc_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def string_cycle_count_d(
        soc: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return cycle_count(soc=soc, grouper=date_local(date_local_5m))

    @method_calc(
        cycle_count=Required(string_cycle_count_d),
    )
    def project_avg_string_cycle_count_d(
        cycle_count: xr.DataArray,
    ):
        return cycle_count.mean(dim=coord(DeviceTypeEnum.BESS_STRING))
