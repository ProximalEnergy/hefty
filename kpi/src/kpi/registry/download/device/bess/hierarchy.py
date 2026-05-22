from core.enumerations import DeviceTypeEnum

from kpi.base.protocol import DeviceProtocol
from kpi.op.download.device.hierarchy import (
    DeviceHierarchyModel,
)
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry


class DownloadDeviceBessHierarchy(FieldRegistry[DeviceProtocol]):
    string_to_pcs = Field(
        DeviceHierarchyModel(
            child_device_type=DeviceTypeEnum.BESS_STRING,
            parent_device_type=DeviceTypeEnum.BESS_PCS,
        )
    )
