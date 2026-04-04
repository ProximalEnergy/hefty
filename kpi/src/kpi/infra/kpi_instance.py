import pandas as pd
from core.database import with_db

from core import models


def kpi_instance_table(
    project_name_shorts: list[str] | None = None,
    kpi_type_ids: list[int] | None = None,
) -> pd.DataFrame:
    columns = [
        "project_name_short",
        "project_id",
        "kpi_type_id",
        "is_visible",
    ]
    if project_name_shorts is not None and len(project_name_shorts) == 0:
        return pd.DataFrame(columns=columns)
    if kpi_type_ids is not None and len(kpi_type_ids) == 0:
        return pd.DataFrame(columns=columns)

    with with_db(schema=None) as db:
        q = (
            db.query(
                models.Project.name_short,
                models.KPIInstance.project_id,
                models.KPIInstance.kpi_type_id,
                models.KPIInstance.is_visible,
            )
            .select_from(models.KPIInstance)
            .join(
                models.Project,
                models.KPIInstance.project_id == models.Project.project_id,
            )
        )
        filters = []
        if project_name_shorts is not None:
            filters.append(models.Project.name_short.in_(project_name_shorts))
        if kpi_type_ids is not None:
            filters.append(models.KPIInstance.kpi_type_id.in_(kpi_type_ids))
        if filters:
            q = q.filter(*filters)
        rows = q.all()

    return pd.DataFrame(
        [
            {
                "project_name_short": name_short,
                "project_id": project_id,
                "kpi_type_id": kpi_type_id,
                "is_visible": is_visible,
            }
            for name_short, project_id, kpi_type_id, is_visible in rows
        ],
        columns=columns,
    )
