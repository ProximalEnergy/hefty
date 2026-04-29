from uuid import UUID

from core.enumerations import ProjectID
from kpi.registry.transform.pv.api import Transform
from kpi.registry.transform.specific_project.bexar import BexarTransform

project_map: dict[UUID, type[Transform]] = {
    ProjectID.BEXAR.value: BexarTransform,
}


def get_transform(project_id: UUID | None = None) -> type[Transform]:
    if project_id is None:
        return Transform
    return project_map.get(project_id, Transform)
