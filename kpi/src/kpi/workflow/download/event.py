from core.enumerations import DeviceType
from kpi.service.download.event import EventSchema, event_model_field

field = event_model_field


class DownloadEventBess(EventSchema):
    pcs_module_offline_event_change_5m = field(
        device_type=DeviceType.BESS_PCS_MODULE,
    )
