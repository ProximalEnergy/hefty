from core.enumerations import DeviceType

from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import OfflineEventModel
from kpi_pipeline.services.schema import DownloadOfflineEventSchema


class DownloadEvents(DownloadOfflineEventSchema):
    bess_pcs_module_offline_event_change_5m = Field(
        OfflineEventModel(
            device_type=DeviceType.BESS_PCS_MODULE,
        )
    )

    bess_pcs_offline_event_change_5m = Field(
        OfflineEventModel(
            device_type=DeviceType.BESS_PCS,
        )
    )
