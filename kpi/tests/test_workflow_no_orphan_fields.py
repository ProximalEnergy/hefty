"""Guard against workflow fields that no KPI upload depends on."""

from kpi.service.schema import outputs
from kpi.workflow.workflow import BaseWorkflow


def test_no_orphan_workflow_fields() -> None:
    """Every defined field must lie on a path to some uploaded KPI field."""
    workflow = BaseWorkflow()
    upload_keys = set(workflow.upload.field_registry().keys())
    inputs = workflow.compile(outputs=upload_keys, delete=False)
    assert not inputs, f"KPI's require these inputs which are not implemented: {inputs}"
    used_for_kpis = outputs(workflow)
    defined = set(workflow.field_registry().keys())
    orphan = defined.difference(used_for_kpis)
    assert not orphan, (
        "Fields are defined but never needed to compute KPI uploads "
        f"(delete or connect them): {sorted(orphan)}"
    )
