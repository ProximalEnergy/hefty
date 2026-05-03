from kpi.base.protocol import CalcProtocol
from kpi.domain.util import fill_missing_zero
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.arg import Required
from kpi.op.transform.method import calc_field
from kpi.registry.download.event import DownloadEvent


class TransformBessCleanEvent(FieldRegistry[CalcProtocol]):
    pcs_offline_event_change_5m = calc_field(fill_missing_zero)(
        Required(DownloadEvent.pcs_offline_event_change_raw_5m),
    )

    pcs_module_offline_event_change_5m = calc_field(fill_missing_zero)(
        Required(DownloadEvent.pcs_module_offline_event_change_raw_5m),
    )

    project_offline_event_change_5m = calc_field(fill_missing_zero)(
        Required(DownloadEvent.project_offline_event_change_raw_5m),
    )
