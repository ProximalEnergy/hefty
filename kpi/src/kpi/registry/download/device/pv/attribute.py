from core.enumerations import DeviceType
from kpi.base.protocol import DeviceProtocol
from kpi.op.download.device.attribute import (
    device_attribute_field,
)
from kpi.op.field_registry import FieldRegistry

from core import models


class DownloadDevicePvAttribute(FieldRegistry[DeviceProtocol]):
    combiner_dc_capacity_raw_kw = device_attribute_field(
        device_type=DeviceType.PV_DC_COMBINER,
        source_field_name=models.Device.capacity_dc.name,
    )

    inverter_ac_capacity_raw_kw = device_attribute_field(
        device_type=DeviceType.PV_INVERTER,
        source_field_name=models.Device.capacity_ac.name,
    )

    inverter_dc_capacity_raw_kw = device_attribute_field(
        device_type=DeviceType.PV_INVERTER,
        source_field_name=models.Device.capacity_dc.name,
    )

    # inverter module

    inverter_module_ac_capacity_raw_kw = device_attribute_field(
        device_type=DeviceType.PV_INVERTER_MODULE,
        source_field_name=models.Device.capacity_ac.name,
    )
