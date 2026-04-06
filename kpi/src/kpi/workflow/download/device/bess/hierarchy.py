from core.enumerations import DeviceType
from kpi.service.download.device.hierarchy import (
    device_hierarchy_field,
)
from kpi.service.download.device.schema import DeviceSchema

field = device_hierarchy_field


class DownloadDeviceBessHierarchy(DeviceSchema):
    string_to_pcs = field(
        child_device_type=DeviceType.BESS_STRING,
        parent_device_type=DeviceType.BESS_PCS,
    )
