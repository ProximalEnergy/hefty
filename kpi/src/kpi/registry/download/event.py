from core.enumerations import DeviceTypeEnum
from kpi.op.download.event import EventsModel
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry


class DownloadEvent(FieldRegistry[EventsModel]):
    pcs_offline_event_change_raw_5m = Field(
        EventsModel(
            device_type=DeviceTypeEnum.BESS_PCS,
        )
    )

    pcs_module_offline_event_change_raw_5m = Field(
        EventsModel(
            device_type=DeviceTypeEnum.BESS_PCS_MODULE,
        )
    )

    project_offline_event_change_raw_5m = Field(
        EventsModel(
            device_type=DeviceTypeEnum.PROJECT,
            project_level=True,
        )
    )
