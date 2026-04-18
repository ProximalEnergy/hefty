"""Guard against workflow fields that no KPI upload depends on."""

from kpi.registry.api import FULL_REGISTRY
from kpi.registry.upload.api import UPLOAD
from kpi.schema.api import BasePipeline


def test_no_orphan_workflow_fields() -> None:
    """Every defined field must lie on a path to some uploaded KPI field."""
    pipeline = BasePipeline()
    upload_keys = set(UPLOAD.keys())
    plan = pipeline.full_plan()
    inputs = plan.trim(upload_keys, delete=False)
    assert not inputs, f"KPI's require these inputs which are not implemented: {inputs}"
    used_for_kpis = plan.outputs()
    defined = set(FULL_REGISTRY.keys())
    orphan = defined.difference(used_for_kpis)
    assert not orphan, (
        "Fields are defined but never needed to compute KPI uploads "
        f"(delete or connect them): {sorted(orphan)}"
    )
