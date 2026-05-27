"""
Status and event-based kpis, namely availability
"""

import xarray as xr
from core.enumerations import DeviceTypeEnum

from kpi.domain.agg.other import daily_mean_across_devices
from kpi.domain.agg.resample import resample_mean
from kpi.domain.bess import perfect_availability_intervals
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import DeviceTypeConstant, grouper, required
from kpi.op.transform.method import MethodCalc, calc_field
from kpi.registry.download.status import DownloadStatus
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


def project_ner_availability_d(
    *,
    availability_5m: xr.DataArray,
    date_local_5m: xr.DataArray,
    epsilon: float = 1e-06,
) -> xr.DataArray:
    """Daily NER availability as mean perfect-interval fraction.

    Used for BESS_PROJECT_NER_AVAILABILITY (125). Periods below nameplate-equivalent
    availability count as imperfect; missing data is excluded from the mean.

    Args:
        availability_5m: Project energy availability at 5-minute resolution.
        date_local_5m: Local date grouper aligned to the time dimension.
        epsilon: Tolerance for perfect availability intervals.

    Returns:
        Daily mean of perfect availability intervals.
    """
    perfect = perfect_availability_intervals(availability_5m, epsilon=epsilon)
    return perfect.groupby(date_local_5m).mean()


class TransformBessSummarizeAvailability(FieldRegistry[MethodCalc]):
    # PCS

    # BESS_PCS_AVAILABILITY (58)
    pcs_availability_d = calc_field(resample_mean)(
        x=required(Eval.pcs_available_5m), grouper=grouper(Eval.date_local_5m)
    )

    project_pcs_availability_d = calc_field(daily_mean_across_devices)(
        value=required(Eval.pcs_available_5m),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.BESS_PCS),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    # PCS Module

    # BESS_PCS_MODULE_AVAILABILITY (107)
    pcs_module_availability_d = calc_field(resample_mean)(
        x=required(Eval.pcs_module_available_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_pcs_module_availability_d = calc_field(daily_mean_across_devices)(
        value=required(Eval.pcs_module_available_5m),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.BESS_PCS_MODULE),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    # Bank

    # BESS_BANK_AVAILABILITY (57)
    bank_availability_d = calc_field(resample_mean)(
        x=required(DownloadStatus.bank_available_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_bank_availability_d = calc_field(daily_mean_across_devices)(
        value=required(DownloadStatus.bank_available_5m),
        device_type=DeviceTypeConstant(value=DeviceTypeEnum.BESS_BANK),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    # Project

    # BESS_PROJECT_POWER_AVAILABILITY (123)

    project_power_availability_d = calc_field(resample_mean)(
        x=required(Eval.project_power_availability_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    # BESS_PROJECT_ENERGY_AVAILABILITY (124)

    project_energy_availability_d = calc_field(resample_mean)(
        x=required(Eval.project_energy_availability_5m),
        grouper=grouper(Eval.date_local_5m),
    )

    project_ner_availability_d = calc_field(project_ner_availability_d)(
        availability_5m=required(Eval.project_energy_availability_5m),
        date_local_5m=grouper(Eval.date_local_5m),
    )

    project_poi_power_availability_d = calc_field(resample_mean)(
        x=required(Eval.project_poi_power_availability_5m),
        grouper=grouper(Eval.date_local_5m),
    )
