from kpi.domain.util import fill_missing_zero
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import required
from kpi.op.transform.method import MethodCalc, calc_field
from kpi.registry.download.event import DownloadEvent


class TransformBessCleanEvent(FieldRegistry[MethodCalc]):
    pcs_offline_event_change_5m = calc_field(fill_missing_zero)(
        required(DownloadEvent.pcs_offline_event_change_raw_5m)
    )

    pcs_module_offline_event_change_5m = calc_field(fill_missing_zero)(
        required(DownloadEvent.pcs_module_offline_event_change_raw_5m)
    )

    project_offline_event_change_5m = calc_field(fill_missing_zero)(
        required(DownloadEvent.project_offline_event_change_raw_5m)
    )
