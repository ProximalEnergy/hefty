from uuid import uuid4

import sqlalchemy as sa
from app._crud.admin.notification_preferences import (
    upsert_bulk_user_notification_preferences_query,
)

from core import enumerations


def test_bulk_notification_preference_upsert_literal_sql_casts_values():
    """Bulk upsert SQL keeps VALUES typed after literal compilation."""
    db_query = upsert_bulk_user_notification_preferences_query(
        user_id="user_123",
        project_ids=[uuid4()],
        notification_type_ids=[1],
        in_app_min_severity=enumerations.NotificationSeverity.WARNING,
    )

    sql = str(
        db_query.query.compile(
            dialect=sa.dialects.postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "CAST(anon_1.project_id AS UUID)" in sql
    assert "CAST(anon_1.notification_type_id AS INTEGER)" in sql
