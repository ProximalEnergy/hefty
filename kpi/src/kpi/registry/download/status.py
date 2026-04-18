from core.enumerations import DeviceType, SensorType
from kpi.op.download.status import StatusModel, status_field
from kpi.op.field_registry import FieldRegistry


class DownloadStatus(FieldRegistry[StatusModel]):
    bank_status_5m = status_field(
        sensor_type=SensorType.BESS_BANK_STATUS,
        device_type=DeviceType.BESS_BANK,
        failure_modes=[87],
    )
