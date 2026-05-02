"""
Status and event-based kpis, namely availability
"""

import numpy as np
import xarray as xr
from core.enumerations import DeviceTypeEnum
from kpi.base.protocol import CalcProtocol
from kpi.domain.util import daily_mean_across_devices, date_local
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.input import Required
from kpi.op.transform.method import method_calc
from kpi.registry.download.status import DownloadStatus
from kpi.registry.transform.bess.evaluate.api import TransformBessEvaluate as Eval


class TransformBessSummarizeAvailability(FieldRegistry[CalcProtocol]):
    # PCS

    # BESS_PCS_AVAILABILITY (58)
    @method_calc(
        availability=Required(Eval.pcs_availability_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def pcs_availability_d(
        availability: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        """
        PCS Availability Per Day
        average of 5-minute interval pcs availability
        """
        return availability.groupby(date_local(date_local_5m)).mean()

    @method_calc(
        availability=Required(Eval.pcs_availability_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_pcs_availability_d(
        availability: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=availability,
            device_type=DeviceTypeEnum.BESS_PCS,
            date_local_5m=date_local_5m,
        )

    # PCS Module

    # BESS_PCS_MODULE_AVAILABILITY (107)
    @method_calc(
        event=Required(Eval.pcs_module_offline_event_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def pcs_module_availability_d(
        event: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return (1 - event).groupby(date_local(date_local_5m)).mean()

    @method_calc(
        event=Required(Eval.pcs_module_offline_event_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_pcs_module_availability_d(
        event: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=(1 - event),
            device_type=DeviceTypeEnum.BESS_PCS_MODULE,
            date_local_5m=date_local_5m,
        )

    # Bank

    # BESS_BANK_AVAILABILITY (57)
    @method_calc(
        status=Required(DownloadStatus.bank_status_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def bank_availability_d(
        status: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return (1 - status).groupby(date_local(date_local_5m)).mean()

    @method_calc(
        status=Required(DownloadStatus.bank_status_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_bank_availability_d(
        status: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=(1 - status),
            device_type=DeviceTypeEnum.BESS_BANK,
            date_local_5m=date_local_5m,
        )

    # Project

    # BESS_PROJECT_POWER_AVAILABILITY (123)

    @method_calc(
        availability=Required(Eval.project_power_availability_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_power_availability_d(
        availability: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project Power Availability Per Day
        Used to calculate BESS_PROJECT_POWER_AVAILABILITY (123).
        average of 5-minute interval project power availability
        """
        return availability.groupby(date_local(date_local_5m)).mean()

    # BESS_PROJECT_ENERGY_AVAILABILITY (124)

    @method_calc(
        availability=Required(Eval.project_energy_availability_5m),
        date_local_5m=Required(Eval.date_local_5m),
    )
    def project_energy_availability_d(
        availability: xr.DataArray,
        date_local_5m: xr.DataArray,
    ) -> xr.DataArray:
        """
        Project Energy Availability Per Day
        Used to calculate BESS_PROJECT_ENERGY_AVAILABILITY (124).
        average of 5-minute interval project energy availability
        """
        return availability.groupby(date_local(date_local_5m)).mean()

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
        return perfect_availability.groupby(date_local(date_local_5m)).mean()
