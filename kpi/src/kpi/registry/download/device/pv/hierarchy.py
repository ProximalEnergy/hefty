from core.enumerations import DeviceType
from kpi.base.protocol import DeviceProtocol
from kpi.op.download.device.hierarchy import (
    device_hierarchy_field,
)
from kpi.op.field_registry import FieldRegistry


class DownloadDevicePvHierarchy(FieldRegistry[DeviceProtocol]):
    combiner_to_inverter = device_hierarchy_field(
        child_device_type=DeviceType.PV_DC_COMBINER,
        parent_device_type=DeviceType.PV_INVERTER,
    )

    inverter_module_to_inverter = device_hierarchy_field(
        child_device_type=DeviceType.PV_INVERTER_MODULE,
        parent_device_type=DeviceType.PV_INVERTER,
    )

    tracker_row_to_block = device_hierarchy_field(
        child_device_type=DeviceType.TRACKER_ROW,
        parent_device_type=DeviceType.PV_BLOCK,
    )

    combiner_to_block = device_hierarchy_field(
        child_device_type=DeviceType.PV_DC_COMBINER,
        parent_device_type=DeviceType.PV_BLOCK,
    )
