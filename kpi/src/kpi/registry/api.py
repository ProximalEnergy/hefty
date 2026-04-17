from kpi.op.schema_registry import Schema, SchemaRegistry
from kpi.registry.download.api import Download
from kpi.registry.transform.api import Transform, get_transform
from kpi.registry.upload.api import Upload


class BaseWorkflow(SchemaRegistry):
    download = Schema(Download)
    transform = Schema(Transform)
    upload = Schema(Upload)


def get_workflow(project_name_short: str | None = None) -> type[BaseWorkflow]:
    class _Workflow(BaseWorkflow):
        transform = Schema(get_transform(project_name_short))

    return _Workflow
