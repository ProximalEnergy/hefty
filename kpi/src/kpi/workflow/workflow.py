from kpi.service.schema_registry import Schema, SchemaRegistry
from kpi.workflow.download.workflow import Download
from kpi.workflow.transform.workflow import Transform, get_transform
from kpi.workflow.upload.workflow import Upload


class BaseWorkflow(SchemaRegistry):
    download = Schema(Download)
    transform = Schema(Transform)
    upload = Schema(Upload)


def get_workflow(project_name_short: str | None = None) -> type[BaseWorkflow]:
    class _Workflow(BaseWorkflow):
        transform = Schema(get_transform(project_name_short))

    return _Workflow
