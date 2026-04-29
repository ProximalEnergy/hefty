from uuid import UUID

from core.crud.operational.projects import get_project
from core.db_query import OutputType

from core import models


def get_project_by_id(*, project_id: UUID) -> models.Project:
    project = get_project(project_id=project_id).get(output_type=OutputType.SQLALCHEMY)
    if project is None:
        raise ValueError(f"Project with id {project_id} not found")
    return project
