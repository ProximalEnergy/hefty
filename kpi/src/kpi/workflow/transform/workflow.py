from kpi.base.enumeration import ProjectNameShort
from kpi.workflow.transform.pv.workflow import Transform
from kpi.workflow.transform.specific_project.bexar import BexarTransform

project_map: dict[str, type[Transform]] = {
    ProjectNameShort.BEXAR.value: BexarTransform,
}


def get_transform(project_name_short: str | None = None) -> type[Transform]:
    if project_name_short is None:
        return Transform
    return project_map.get(project_name_short, Transform)
