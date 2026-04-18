from kpi.op.upload import UploadModel, merge_upload_maps_strict
from kpi.registry.upload.bess.api import UPLOAD_BESS
from kpi.registry.upload.pv import UPLOAD_PV

UPLOAD: dict[str, UploadModel] = merge_upload_maps_strict(
    maps=[UPLOAD_BESS, UPLOAD_PV]
)
