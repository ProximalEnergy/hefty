from uuid import UUID

from core.enumerations import ProjectID
from kpi.registry.transform.pv.api import Transform
from kpi.registry.transform.specific_project.bexar import BexarTransform
from kpi.registry.transform.specific_project.double_black_diamond import (
    DoubleBlackDiamondTransform,
)

project_map: dict[UUID, type[Transform]] = {
    ProjectID.BEXAR.value: BexarTransform,
    ProjectID.DOUBLE_BLACK_DIAMOND.value: DoubleBlackDiamondTransform,
}


def get_transform(project_id: UUID | None = None) -> type[Transform]:
    if project_id is None:
        return Transform
    return project_map.get(project_id, Transform)
