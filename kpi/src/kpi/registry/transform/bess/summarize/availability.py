"""
Status and event-based kpis, namely availability
"""

import numpy as np
import xarray as xr
from core.enumerations import DeviceType
from kpi.base.protocol import CalcProtocol
from kpi.domain.util import daily_mean_across_devices, date_local
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.method import method_calc, required
from kpi.registry.download.status import DownloadStatus
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


class TransformBessSummarizeAvailability(FieldRegistry[CalcProtocol]):
    # PCS

    # BESS_PCS_AVAILABILITY (58)
    @method_calc
    def pcs_availability_d(
        availability: xr.DataArray = required(Eval.pcs_availability_5m),
        date_local_5m: xr.DataArray = required(Eval.date_local_5m),
    ) -> xr.DataArray:
        """
        PCS Availability Per Day
        average of 5-minute interval pcs availability
        """
        return availability.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_pcs_availability_d(
        availability: xr.DataArray = required(Eval.pcs_availability_5m),
        date_local_5m: xr.DataArray = required(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=availability,
            device_type=DeviceType.BESS_PCS,
            date_local_5m=date_local_5m,
        )

    # PCS Module

    # BESS_PCS_MODULE_AVAILABILITY (107)
    @method_calc
    def pcs_module_availability_d(
        event: xr.DataArray = required(Eval.pcs_module_offline_event_5m),
        date_local_5m: xr.DataArray = required(Eval.date_local_5m),
    ) -> xr.DataArray:
        return (1 - event).groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_pcs_module_availability_d(
        event: xr.DataArray = required(Eval.pcs_module_offline_event_5m),
        date_local_5m: xr.DataArray = required(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=(1 - event),
            device_type=DeviceType.BESS_PCS_MODULE,
            date_local_5m=date_local_5m,
        )

    # Bank

    # BESS_BANK_AVAILABILITY (57)
    @method_calc
    def bank_availability_d(
        status: xr.DataArray = required(DownloadStatus.bank_status_5m),
        date_local_5m: xr.DataArray = required(Eval.date_local_5m),
    ) -> xr.DataArray:
        return (1 - status).groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_bank_availability_d(
        status: xr.DataArray = required(DownloadStatus.bank_status_5m),
        date_local_5m: xr.DataArray = required(Eval.date_local_5m),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=(1 - status),
            device_type=DeviceType.BESS_BANK,
            date_local_5m=date_local_5m,
        )

    # Project

    # BESS_PROJECT_POWER_AVAILABILITY (123)

    @method_calc
    def project_power_availability_d(
        availability: xr.DataArray = required(Eval.project_power_availability_5m),
        date_local_5m: xr.DataArray = required(Eval.date_local_5m),
    ) -> xr.DataArray:
        """
        Project Power Availability Per Day
        Used to calculate BESS_PROJECT_POWER_AVAILABILITY (123).
        average of 5-minute interval project power availability
        """
        return availability.groupby(date_local(date_local_5m)).mean()

    # BESS_PROJECT_ENERGY_AVAILABILITY (124)

    @method_calc
    def project_energy_availability_d(
        availability: xr.DataArray = required(Eval.project_energy_availability_5m),
        date_local_5m: xr.DataArray = required(Eval.date_local_5m),
    ) -> xr.DataArray:
        """
        Project Energy Availability Per Day
        Used to calculate BESS_PROJECT_ENERGY_AVAILABILITY (124).
        average of 5-minute interval project energy availability
        """
        return availability.groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_ner_availability_d(
        availability_5m: xr.DataArray = required(Eval.project_pcs_availability_5m),
        date_local_5m: xr.DataArray = required(Eval.date_local_5m),
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
        return perfect_availability.groupby(date_local(date_local_5m)).mean()
