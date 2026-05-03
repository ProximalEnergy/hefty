"""
Status and event-based kpis, namely availability
"""

import numpy as np
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.protocol import CalcProtocol
from kpi.domain.agg.other import daily_mean_across_devices
from kpi.domain.agg.resample import resample_mean
from kpi.domain.util import rename
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Constant, Required
from kpi.op.transform.method import calc_field, method_calc
from kpi.registry.download.status import DownloadStatus
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


class TransformBessSummarizeAvailability(FieldRegistry[CalcProtocol]):
    # PCS

    # BESS_PCS_AVAILABILITY (58)
    pcs_availability_d = calc_field(resample_mean)(
        x=Required(Eval.pcs_available_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_pcs_availability_d = calc_field(daily_mean_across_devices)(
        value=Required(Eval.pcs_available_5m),
        device_type=Constant(DeviceTypeEnum.BESS_PCS),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # PCS Module

    # BESS_PCS_MODULE_AVAILABILITY (107)
    pcs_module_availability_d = calc_field(resample_mean)(
        x=Required(Eval.pcs_module_available_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_pcs_module_availability_d = calc_field(daily_mean_across_devices)(
        value=Required(Eval.pcs_module_available_5m),
        device_type=Constant(DeviceTypeEnum.BESS_PCS_MODULE),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # Bank

    # BESS_BANK_AVAILABILITY (57)
    bank_availability_d = calc_field(resample_mean)(
        x=Required(DownloadStatus.bank_available_5m),
        grouper=Required(Eval.date_local_5m),
    )

    project_bank_availability_d = calc_field(daily_mean_across_devices)(
        value=Required(DownloadStatus.bank_available_5m),
        device_type=Constant(DeviceTypeEnum.BESS_BANK),
        date_local_5m=Required(Eval.date_local_5m),
    )

    # Project

    # BESS_PROJECT_POWER_AVAILABILITY (123)

    project_power_availability_d = calc_field(resample_mean)(
        x=Required(Eval.project_power_availability_5m),
        grouper=Required(Eval.date_local_5m),
    )

    # BESS_PROJECT_ENERGY_AVAILABILITY (124)

    project_energy_availability_d = calc_field(resample_mean)(
        x=Required(Eval.project_energy_availability_5m),
        grouper=Required(Eval.date_local_5m),
    )

    @method_calc(
        availability_5m=Required(Eval.project_system_availability_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_ner_availability_d(
        availability_5m: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project NER Availability Per Day
        Used to calculate BESS_PROJECT_NER_AVAILABILITY (125).
        Percentage of day where availability is 100%.
        Any offline underperformance event prevents the project
        from discharging at nameplate power (required by
        Technical Performance Metrics in Exhibit 7) making it
        an exclusion. See Section III bb.
        Periods with missing availability data are excluded
        from the calculation.
        """
        epsilon = 1e-6
        perfect_availability = xr.where(
            availability_5m >= 1 - epsilon,
            1.0,
            xr.where(availability_5m < 1 - epsilon, 0.0, np.nan),
        )
        return perfect_availability.groupby(rename(date_local_5m)).mean()
