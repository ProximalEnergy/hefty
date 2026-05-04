from kpi.registry.download.api import DownloadRegistry
from kpi.registry.transform.api import Transform
from kpi.registry.upload.api import UPLOAD

FULL_REGISTRY = {
    **DownloadRegistry.map(),
    **Transform.map(),
    **UPLOAD,
}
