from kpi.infra.download.tenaska import GENERATOR_URL, VIRTUAL_URL
from kpi.op.download.device.schema import DeviceSchema
from kpi.op.download.event import EventSchema
from kpi.op.download.expected_energy import ExpectedEnergySchema
from kpi.op.download.project_attribute import ProjectAttributeSchema
from kpi.op.download.sensor import SensorSchema
from kpi.op.download.status import StatusSchema
from kpi.op.download.tenaska import TenaskaSchema
from kpi.op.pipeline_schema import PipelineSchema
from kpi.registry.download.device.api import DownloadDevice
from kpi.registry.download.event import DownloadEvent
from kpi.registry.download.expected_energy import DownloadExpectedEnergy
from kpi.registry.download.project_attribute.api import DownloadProjectAttribute
from kpi.registry.download.sensor.api import DownloadSensor
from kpi.registry.download.status import DownloadStatus
from kpi.registry.download.tenaska.generator import DownloadTenaskaGenerator
from kpi.registry.download.tenaska.virtual import DownloadTenaskaVirtual

download_schema = PipelineSchema(
    map={
        "event": EventSchema(map=DownloadEvent.map()),
        "expected_energy": ExpectedEnergySchema(map=DownloadExpectedEnergy.map()),
        "device": DeviceSchema(map=DownloadDevice.map()),
        "project_attribute": ProjectAttributeSchema(map=DownloadProjectAttribute.map()),
        "sensor": SensorSchema(map=DownloadSensor.map()),
        "status": StatusSchema(map=DownloadStatus.map()),
        "tenaska_generator": TenaskaSchema(
            map=DownloadTenaskaGenerator.map(), url=GENERATOR_URL
        ),
        "tenaska_virtual": TenaskaSchema(
            map=DownloadTenaskaVirtual.map(), url=VIRTUAL_URL
        ),
    }
)
