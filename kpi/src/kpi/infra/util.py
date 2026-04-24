from core.crud.operational.projects import get_projects
from core.db_query import OutputType
from core.utils.pandas_datetime import index_to_numpy_ns, series_to_numpy_ns

from core import models


def get_project_from_database(name_short: str) -> models.Project:
    query = get_projects(name_short=name_short)
    projects = query.get(output_type=OutputType.SQLALCHEMY)
    if projects is None or len(projects) != 1:
        raise ValueError(
            f"Expected 1 project, got {len(projects) if projects is not None else 0}"
        )
    project = projects[0]
    return project
