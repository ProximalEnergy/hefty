import xarray as xr
from kpi.base.protocol import CalcProtocol
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.method import Input, method_calc
from kpi.registry.download.event import DownloadEvent


class TransformBessCleanEvent(FieldRegistry[CalcProtocol]):
    @method_calc
    def pcs_offline_event_change_5m(
        offline_event_change: xr.DataArray = Input(
            DownloadEvent.pcs_offline_event_change_raw_5m
        ),
    ) -> xr.DataArray:
        """
        PCS Offline Event Change Per 5-Minute Interval
        Fill missing values with 0.
        """
        return offline_event_change.fillna(0)

    @method_calc
    def pcs_module_offline_event_change_5m(
        offline_event_change: xr.DataArray = Input(
            DownloadEvent.pcs_module_offline_event_change_raw_5m
        ),
    ) -> xr.DataArray:
        """
        PCS Module Offline Event Change Per 5-Minute Interval
        Fill missing values with 0.
        """
        return offline_event_change.fillna(0)
