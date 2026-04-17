import xarray as xr
from kpi.op.transform.method import Input, method_calc
from kpi.op.transform.schema import CalcSchema
from kpi.registry.download.event import DownloadEventBess


class TransformBessCleanEvent(CalcSchema):
    @method_calc
    def pcs_offline_event_change_5m(
        offline_event_change: xr.DataArray = Input(
            DownloadEventBess.pcs_offline_event_change_raw_5m
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
            DownloadEventBess.pcs_module_offline_event_change_raw_5m
        ),
    ) -> xr.DataArray:
        """
        PCS Module Offline Event Change Per 5-Minute Interval
        Fill missing values with 0.
        """
        return offline_event_change.fillna(0)
