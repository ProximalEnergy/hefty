from core.enumerations import DeviceTypeEnum
from kpi.base.protocol import DeviceProtocol
from kpi.op.download.device.hierarchy import (
    DeviceHierarchyModel,
)
from kpi.op.field import Field
from kpi.op.field_registry import FieldRegistry


class DownloadDevicePvHierarchy(FieldRegistry[DeviceProtocol]):
    combiner_to_inverter = Field[DeviceProtocol](
        DeviceHierarchyModel(
            child_device_type=DeviceTypeEnum.PV_DC_COMBINER,
            parent_device_type=DeviceTypeEnum.PV_INVERTER,
        )
    )

    inverter_module_to_inverter = Field[DeviceProtocol](
        DeviceHierarchyModel(
            child_device_type=DeviceTypeEnum.PV_INVERTER_MODULE,
            parent_device_type=DeviceTypeEnum.PV_INVERTER,
        )
    )

    tracker_row_to_block = Field[DeviceProtocol](
        DeviceHierarchyModel(
            child_device_type=DeviceTypeEnum.TRACKER_ROW,
            parent_device_type=DeviceTypeEnum.PV_BLOCK,
        )
    )

    combiner_to_block = Field[DeviceProtocol](
        DeviceHierarchyModel(
            child_device_type=DeviceTypeEnum.PV_DC_COMBINER,
            parent_device_type=DeviceTypeEnum.PV_BLOCK,
        )
    )
