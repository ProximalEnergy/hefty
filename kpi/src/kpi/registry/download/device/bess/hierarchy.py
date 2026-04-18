from core.enumerations import DeviceType
from kpi.base.protocol import DeviceProtocol
from kpi.op.download.device.hierarchy import (
    device_hierarchy_field,
)
from kpi.op.field_registry import FieldRegistry


class DownloadDeviceBessHierarchy(FieldRegistry[DeviceProtocol]):
    string_to_pcs = device_hierarchy_field(
        child_device_type=DeviceType.BESS_STRING,
        parent_device_type=DeviceType.BESS_PCS,
    )
