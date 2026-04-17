from kpi.registry.upload.bess.other import UploadBessOther
from kpi.registry.upload.bess.pcs import UploadBessPcs
from kpi.registry.upload.bess.project import UploadBessProject
from kpi.registry.upload.bess.string import UploadBessString


class UploadBess(
    UploadBessString,
    UploadBessProject,
    UploadBessPcs,
    UploadBessOther,
):
    """Combined BESS upload registries (string, project, PCS, other)."""
