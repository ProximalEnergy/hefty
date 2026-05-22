from core.enumerations import DeviceTypeEnum, SensorTypeEnum

from kpi.op.download.status import StatusModel
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry


class DownloadStatus(FieldRegistry[StatusModel]):
    bank_available_5m = Field(
        StatusModel(
            sensor_type=SensorTypeEnum.BESS_BANK_STATUS,
            device_type=DeviceTypeEnum.BESS_BANK,
            failure_modes=[87],
        )
    )
