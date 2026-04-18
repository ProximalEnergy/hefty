from kpi.registry.download.api import Download
from kpi.registry.transform.api import Transform
from kpi.registry.upload.api import UPLOAD

FULL_REGISTRY = {
    **Download.map(),
    **Transform.map(),
    **UPLOAD,
}
