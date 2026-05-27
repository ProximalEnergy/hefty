from uuid import UUID

from kpi.op.pipeline_schema import PipelineSchema
from kpi.op.transform.schema import CalcSchema
from kpi.op.upload import UploadSchema
from kpi.registry.transform.api import Transform, get_transform
from kpi.registry.upload.api import UPLOAD
from kpi.schema.download import download_schema

base_map = {
    "download": download_schema,
    "transform": CalcSchema(map=Transform.map()),
    "upload": UploadSchema(map=UPLOAD),
}

base_pipeline = PipelineSchema(map=base_map)


def get_pipeline(project_id: UUID) -> PipelineSchema:
    new_transform = CalcSchema(map=get_transform(project_id).map())
    return PipelineSchema(map=base_map | {"transform": new_transform})
