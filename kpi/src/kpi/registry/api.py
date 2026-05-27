from kpi.base.protocol import NodeProtocol
from kpi.registry.download.api import DownloadRegistry
from kpi.registry.transform.api import Transform
from kpi.registry.upload.api import UPLOAD

FULL_REGISTRY: dict[str, NodeProtocol] = {
    **DownloadRegistry.map(),
    **Transform.map(),
    **UPLOAD,
}
