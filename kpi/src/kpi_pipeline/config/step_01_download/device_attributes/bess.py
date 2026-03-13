from core.models import Device

from kpi_pipeline.base.enums import DeviceType
from kpi_pipeline.base.field import Field
from kpi_pipeline.base.models import DeviceAttributeModel
from kpi_pipeline.services.schema import DownloadDeviceAttributesSchema


class DownloadDevAttrsBESS(DownloadDeviceAttributesSchema):
    bess_pcs_energy_capacity_kwh = Field(
        DeviceAttributeModel(
            device_type=DeviceType.BESS_PCS,
            source_field_name=Device.capacity_ac.name,
        ),
    )

    bess_pcs_module_energy_capacity_kwh = Field(
        DeviceAttributeModel(
            device_type=DeviceType.BESS_PCS_MODULE,
            source_field_name=Device.capacity_ac.name,
        ),
    )

    bess_string_energy_capacity_kwh = Field(
        DeviceAttributeModel(
            device_type=DeviceType.BESS_STRING,
            source_field_name=Device.capacity_dc.name,
        ),
    )

    bess_pcs_power_capacity_kw = Field(
        DeviceAttributeModel(
            device_type=DeviceType.BESS_PCS,
            source_field_name=Device.capacity_ac.name,
        ),
    )

    bess_string_power_capacity_kw = Field(
        DeviceAttributeModel(
            device_type=DeviceType.BESS_STRING,
            source_field_name=Device.capacity_ac.name,
        ),
    )

    bess_mv_circuit_power_capacity_kw = Field(
        DeviceAttributeModel(
            device_type=DeviceType.BESS_MV_CIRCUIT_METER,
            source_field_name=Device.capacity_ac.name,
        ),
    )
