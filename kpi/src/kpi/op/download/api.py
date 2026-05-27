from kpi.op.download.device.schema import DeviceSchema
from kpi.op.download.event import EventSchema
from kpi.op.download.expected_energy import ExpectedEnergySchema
from kpi.op.download.project_attribute import ProjectAttributeSchema
from kpi.op.download.sensor import SensorSchema
from kpi.op.download.status import StatusSchema
from kpi.op.download.tenaska import TenaskaSchema

DownloadSchemaType = (
    EventSchema
    | ExpectedEnergySchema
    | DeviceSchema
    | ProjectAttributeSchema
    | SensorSchema
    | StatusSchema
    | TenaskaSchema
)
