from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models


def get_pg_data_type(*, db: Session, pg_data_type_id: int):
    """Fetch a single PG data type by its identifier.

    Args:
        db: Synchronous database session bound to the operational schema.
        pg_data_type_id: Primary key of the PG data type to retrieve.
    """
    statement = select(models.PGDataType).where(
        models.PGDataType.pg_data_type_id == pg_data_type_id,
    )
    return db.execute(statement).scalar_one_or_none()


def get_pg_data_types(
    *,
    db: Session,
    pg_data_type_ids: list[int] = [],
    name_short: str = "",
):
    """List PG data types optionally filtered by ID or short name.

    Args:
        db: Synchronous database session bound to the operational schema.
        pg_data_type_ids: Filter to this set of PG data type IDs when provided.
        name_short: Filter by the PG data type short name when provided.
    """
    statement = select(models.PGDataType)
    if pg_data_type_ids:
        statement = statement.where(
            models.PGDataType.pg_data_type_id.in_(pg_data_type_ids),
        )
    if name_short:
        statement = statement.where(models.PGDataType.name_short == name_short)
    return db.execute(statement).scalars().all()
