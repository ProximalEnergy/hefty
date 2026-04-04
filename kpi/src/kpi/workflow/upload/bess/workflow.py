from kpi.workflow.upload.bess.other import UploadBessOther
from kpi.workflow.upload.bess.pcs import UploadBessPcs
from kpi.workflow.upload.bess.project import UploadBessProject
from kpi.workflow.upload.bess.string import UploadBessString


class UploadBess(
    UploadBessString,
    UploadBessProject,
    UploadBessPcs,
    UploadBessOther,
):
    """Combined BESS upload registries (string, project, PCS, other)."""
