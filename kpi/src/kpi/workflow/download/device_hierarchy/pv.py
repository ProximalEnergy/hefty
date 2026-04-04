from core.enumerations import DeviceType
from kpi.service.download.device_hierarchy import (
    DeviceHierarchySchema,
    device_hierarchy_field,
)

field = device_hierarchy_field


class DownloadDeviceHierarchyPv(DeviceHierarchySchema):
    combiner_to_inverter = field(
        child_device_type=DeviceType.PV_DC_COMBINER,
        parent_device_type=DeviceType.PV_INVERTER,
    )

    inverter_module_to_inverter = field(
        child_device_type=DeviceType.PV_INVERTER_MODULE,
        parent_device_type=DeviceType.PV_INVERTER,
    )

    tracker_row_to_block = field(
        child_device_type=DeviceType.TRACKER_ROW,
        parent_device_type=DeviceType.PV_BLOCK,
    )

    combiner_to_block = field(
        child_device_type=DeviceType.PV_DC_COMBINER,
        parent_device_type=DeviceType.PV_BLOCK,
    )
