from typing import TYPE_CHECKING

from kpi.base.protocol import SchemaClassProtocol, SchemaProtocol
from kpi.service.download.device.schema import DeviceSchema
from kpi.service.download.event import EventSchema
from kpi.service.download.expected_energy import ExpectedEnergySchema
from kpi.service.download.project_attribute import ProjectAttributeSchema
from kpi.service.download.sensor import SensorSchema
from kpi.service.download.status import StatusSchema
from kpi.service.schema_registry import SchemaRegistry
from kpi.service.transform.schema import CalcSchema
from kpi.service.upload import UploadSchema

if TYPE_CHECKING:
    _device_class: SchemaClassProtocol = DeviceSchema
    _device_schema: SchemaProtocol = DeviceSchema()

    _event_class: SchemaClassProtocol = EventSchema
    _event_schema: SchemaProtocol = EventSchema()

    _expected_energy_class: SchemaClassProtocol = ExpectedEnergySchema
    _expected_energy_schema: SchemaProtocol = ExpectedEnergySchema()

    _project_attribute_class: SchemaClassProtocol = ProjectAttributeSchema
    _project_attribute_schema: SchemaProtocol = ProjectAttributeSchema()

    _status_class: SchemaClassProtocol = StatusSchema
    _status_schema: SchemaProtocol = StatusSchema()

    _sensor_class: SchemaClassProtocol = SensorSchema
    _sensor_schema: SchemaProtocol = SensorSchema()

    _calc_class: SchemaClassProtocol = CalcSchema
    _calc_schema: SchemaProtocol = CalcSchema()

    _schema_class: SchemaClassProtocol = SchemaRegistry
    _schema_registry: SchemaProtocol = SchemaRegistry()

    _upload_class: SchemaClassProtocol = UploadSchema
    _upload_schema: SchemaProtocol = UploadSchema()
