from core.enumerations import DeviceType
from kpi.service.download.device_hierarchy import (
    DeviceHierarchySchema,
    device_hierarchy_field,
)

field = device_hierarchy_field


class DownloadDeviceHierarchyBess(DeviceHierarchySchema):
    string_to_pcs = field(
        child_device_type=DeviceType.BESS_STRING,
        parent_device_type=DeviceType.BESS_PCS,
    )
