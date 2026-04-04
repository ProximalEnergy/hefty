from kpi.workflow.upload.bess.workflow import UploadBess
from kpi.workflow.upload.pv import UploadPv


class Upload(UploadPv, UploadBess):
    """Full KPI upload registry (PV and BESS)."""
