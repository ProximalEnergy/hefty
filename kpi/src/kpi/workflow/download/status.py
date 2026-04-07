from core.enumerations import DeviceType, SensorType
from kpi.service.download.status import StatusSchema, status_field

field = status_field

pcs_module_failure_modes = [96] + list(range(100, 205))


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

    pcs_module_offline_status_5m = field(
        sensor_type=SensorType.BESS_PCS_MODULE_STATUS,
        device_type=DeviceType.BESS_PCS_MODULE,
        failure_modes=pcs_module_failure_modes,
    )

    pcs_module_offline_alarm_5m = field(
        sensor_type=SensorType.BESS_PCS_MODULE_ALARM,
        device_type=DeviceType.BESS_PCS_MODULE,
        failure_modes=pcs_module_failure_modes,
    )

    string_status_5m = field(
        sensor_type=SensorType.BESS_STRING_STATUS,
        device_type=DeviceType.BESS_STRING,
        failure_modes=[89],
    )
