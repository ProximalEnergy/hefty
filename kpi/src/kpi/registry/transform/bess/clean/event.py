from kpi.base.protocol import CalcProtocol
from kpi.domain.util import fill_missing_zero
from kpi.op.field_registry import FieldRegistry
from kpi.op.transform.unary import unary_field
from kpi.registry.download.event import DownloadEvent


class TransformBessCleanEvent(FieldRegistry[CalcProtocol]):
    pcs_offline_event_change_5m = unary_field(
        fill_missing_zero,
        field=DownloadEvent.pcs_offline_event_change_raw_5m,
    )

    pcs_module_offline_event_change_5m = unary_field(
        fill_missing_zero,
        field=DownloadEvent.pcs_module_offline_event_change_raw_5m,
    )

    project_offline_event_change_5m = unary_field(
        fill_missing_zero,
        field=DownloadEvent.project_offline_event_change_raw_5m,
    )
