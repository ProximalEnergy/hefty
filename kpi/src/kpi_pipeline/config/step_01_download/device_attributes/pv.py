from core import models
from kpi_pipeline.base.enums import DeviceType
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import DeviceAttributeModel
from kpi_pipeline.services.schema import DownloadDeviceAttributesSchema


class DownloadDeviceAttrsPV(DownloadDeviceAttributesSchema):
    pv_dc_combiner_power_capacity_dc_kw = Field(
        DeviceAttributeModel(
            source_field_name=models.Device.capacity_dc.name,
            device_type=DeviceType.PV_DC_COMBINER,
        )
    )

    pv_inverter_ac_capacity_kw = Field(
        DeviceAttributeModel(
            source_field_name=models.Device.capacity_ac.name,
            device_type=DeviceType.PV_INVERTER,
        )
    )

    pv_inverter_dc_capacity_kw = Field(
        DeviceAttributeModel(
            source_field_name=models.Device.capacity_dc.name,
            device_type=DeviceType.PV_INVERTER,
        )
    )

    # pcs module

    pv_inverter_module_power_ac_capacity_kw = Field(
        DeviceAttributeModel(
            source_field_name=models.Device.capacity_ac.name,
            device_type=DeviceType.PV_INVERTER_MODULE,
        )
    )
