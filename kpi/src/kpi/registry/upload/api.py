from kpi.registry.upload.bess.api import UploadBess
from kpi.registry.upload.pv import UploadPv


class Upload(UploadPv, UploadBess):
    """Full KPI upload registry (PV and BESS)."""
