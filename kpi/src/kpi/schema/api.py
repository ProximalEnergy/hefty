from kpi.op.pipeline_schema import PipelineSchema, Schema
from kpi.op.transform.schema import CalcSchema
from kpi.op.upload import UploadSchema
from kpi.registry.transform.api import Transform, get_transform
from kpi.registry.upload.api import UPLOAD
from kpi.schema.download import Download


class BasePipeline(PipelineSchema):
    download = Schema(Download())
    transform = Schema(CalcSchema(map=Transform.map()))
    upload = Schema(UploadSchema(map=UPLOAD))


def get_pipeline(project_name_short: str) -> type[BasePipeline]:
    class _Pipeline(BasePipeline):
        transform = Schema(CalcSchema(map=get_transform(project_name_short).map()))

    return _Pipeline
