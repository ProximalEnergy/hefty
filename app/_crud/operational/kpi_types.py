from sqlalchemy.orm import Session, noload, selectinload

from core import models


def _get_kpi_types_options(*, deep: bool):
    if deep:
        options = (selectinload(models.KPIType.device_type),)
    else:
        options = (noload(models.KPIType.device_type),)

    return options


def get_kpi_types(
    db: Session,
    *,
    kpi_type_ids: list[int] | None = None,
    deep: bool = False,
):
    options = _get_kpi_types_options(deep=deep)

    query = db.query(models.KPIType).options(*options)

    if kpi_type_ids is not None:
        query = query.filter(models.KPIType.kpi_type_id.in_(kpi_type_ids))

    return query.all()
