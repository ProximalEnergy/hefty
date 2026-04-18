from core.enumerations import DeviceType
from kpi.op.download.event import EventsModel, event_model_field
from kpi.op.field_registry import FieldRegistry


class DownloadEvent(FieldRegistry[EventsModel]):
    pcs_offline_event_change_raw_5m = event_model_field(
        device_type=DeviceType.BESS_PCS,
    )

    pcs_module_offline_event_change_raw_5m = event_model_field(
        device_type=DeviceType.BESS_PCS_MODULE,
    )
