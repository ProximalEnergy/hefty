from kpi.op.schema_registry import Schema, SchemaRegistry
from kpi.registry.download.device.api import DownloadDevice
from kpi.registry.download.event import DownloadEventBess
from kpi.registry.download.expected_energy import DownloadExpectedEnergy
from kpi.registry.download.project_attribute.api import DownloadProjectAttribute
from kpi.registry.download.sensor.api import DownloadSensor
from kpi.registry.download.status import DownloadStatusBess


class Download(SchemaRegistry):
    device = Schema(DownloadDevice)
    event = Schema(DownloadEventBess)
    expected_energy = Schema(DownloadExpectedEnergy)
    project_attribute = Schema(DownloadProjectAttribute)
    sensor = Schema(DownloadSensor)
    status = Schema(DownloadStatusBess)
