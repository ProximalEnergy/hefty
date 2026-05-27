"""Contract tests for operational KPI data CRUD."""

import datetime

from core.crud.operational.kpi_data import core_get_kpi_data
from sqlalchemy.dialects import postgresql


def test_core_get_kpi_data_empty_project_ids_cannot_match_all_projects() -> None:
    """An empty project scope must compile to a query that returns no rows."""
    db_query = core_get_kpi_data(
        start=datetime.date(2026, 1, 1),
        end=datetime.date(2026, 1, 2),
        project_ids=[],
        kpi_type_ids=[],
        include_device_data=True,
    )

    compiled_query = str(
        db_query.query.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        ),
    )

    assert "false" in compiled_query.lower()
