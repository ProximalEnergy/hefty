from kpi.op.upload import UploadModel, merge_upload_maps_strict
from kpi.registry.upload.bess.other import UPLOAD_BESS_OTHER
from kpi.registry.upload.bess.pcs import UPLOAD_BESS_PCS
from kpi.registry.upload.bess.project import UPLOAD_BESS_PROJECT
from kpi.registry.upload.bess.string import UPLOAD_BESS_STRING

UPLOAD_BESS: dict[str, UploadModel] = merge_upload_maps_strict(
    maps=[
        UPLOAD_BESS_OTHER,
        UPLOAD_BESS_PCS,
        UPLOAD_BESS_PROJECT,
        UPLOAD_BESS_STRING,
    ]
)
