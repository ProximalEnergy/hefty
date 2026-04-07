from core.enumerations import DeviceType, SensorType
from kpi.service.download.status import StatusSchema, status_field

field = status_field


class DownloadStatusBess(StatusSchema):
    bank_status_5m = field(
        sensor_type=SensorType.BESS_BANK_STATUS,
        device_type=DeviceType.BESS_BANK,
        failure_modes=[87],
    )

    pcs_status_5m = field(
        sensor_type=SensorType.BESS_PCS_STATUS,
        device_type=DeviceType.BESS_PCS,
        failure_modes=[91],
    )
