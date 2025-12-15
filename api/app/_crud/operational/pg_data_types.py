from sqlalchemy.orm import Session

from core import models


def get_pg_data_type(*, db: Session, pg_data_type_id: int):
    """todo

    Args:
        db: TODO: describe.
        pg_data_type_id: TODO: describe.
    """
    return (
        db.query(models.PGDataType)
        .filter(models.PGDataType.pg_data_type_id == pg_data_type_id)
        .first()
    )


def get_pg_data_types(
    db: Session,
    *,
    pg_data_type_ids: list[int] = [],
    name_short: str = "",
):
    """todo

    Args:
        db: TODO: describe.
        pg_data_type_ids: TODO: describe.
        name_short: TODO: describe.
    """
    query = db.query(models.PGDataType)
    if pg_data_type_ids:
        query = query.filter(models.PGDataType.pg_data_type_id.in_(pg_data_type_ids))
    if name_short:
        query = query.filter(models.PGDataType.name_short == name_short)
    return query.all()
