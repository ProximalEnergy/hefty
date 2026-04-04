"""
Status and event-based kpis, namely availability
"""

import xarray as xr
from core.enumerations import DeviceType
from kpi.domain.util import daily_mean_across_devices, date_local
from kpi.service.transform.method import Input, method_calc
from kpi.service.transform.schema import CalcSchema
from kpi.workflow.download.event import DownloadEventBess
from kpi.workflow.download.status import DownloadStatusBess
from kpi.workflow.transform.bess.evaluate.evaluate import TransformBessEvaluate as Eval


class TransformBessSummarizeAvailability(CalcSchema):
    # BESS_PCS_AVAILABILITY (58)
    @method_calc
    def pcs_availability_d(
        status: xr.DataArray = Input(DownloadStatusBess.pcs_status_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (1 - status).groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_pcs_availability_d(
        status: xr.DataArray = Input(DownloadStatusBess.pcs_status_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=(1 - status),
            device_type=DeviceType.BESS_PCS,
            date_local_5m=date_local_5m,
        )

    # BESS_PCS_MODULE_AVAILABILITY (107)
    @method_calc
    def pcs_module_availability_d(
        event: xr.DataArray = Input(
            DownloadEventBess.pcs_module_offline_event_change_5m.name
        ),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (1 - event).groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_pcs_module_availability_d(
        event: xr.DataArray = Input(
            DownloadEventBess.pcs_module_offline_event_change_5m.name
        ),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=(1 - event),
            device_type=DeviceType.BESS_PCS_MODULE,
            date_local_5m=date_local_5m,
        )

    # BESS_BANK_AVAILABILITY (57)
    @method_calc
    def bank_availability_d(
        status: xr.DataArray = Input(DownloadStatusBess.bank_status_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return (1 - status).groupby(date_local(date_local_5m)).mean()

    @method_calc
    def project_bank_availability_d(
        status: xr.DataArray = Input(DownloadStatusBess.bank_status_5m.name),
        date_local_5m: xr.DataArray = Input(Eval.date_local_5m.name),
    ) -> xr.DataArray:
        return daily_mean_across_devices(
            value=(1 - status),
            device_type=DeviceType.BESS_BANK,
            date_local_5m=date_local_5m,
        )
