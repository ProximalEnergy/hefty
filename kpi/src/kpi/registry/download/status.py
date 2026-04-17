from core.enumerations import DeviceType, SensorType
from kpi.op.download.status import StatusSchema, status_field

field = status_field


class DownloadStatusBess(StatusSchema):
    bank_status_5m = field(
        sensor_type=SensorType.BESS_BANK_STATUS,
        device_type=DeviceType.BESS_BANK,
        failure_modes=[87],
    )
