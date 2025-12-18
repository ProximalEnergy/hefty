from sqlalchemy.orm import Session, noload, selectinload

from core import models


def _get_kpi_types_options(*, deep: bool):
    """Build loader options for KPI type queries.

    Args:
        deep: Whether to eagerly load related device types.
    """
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
    """Fetch KPI types with optional filtering and relationship loading.

    Args:
        db: Synchronous database session bound to the operational schema.
        kpi_type_ids: Optional list of KPI type IDs to filter the query.
        deep: When True, include device type relationships in the result.
    """
    options = _get_kpi_types_options(deep=deep)

    query = db.query(models.KPIType).options(*options)

    if kpi_type_ids is not None:
        query = query.filter(models.KPIType.kpi_type_id.in_(kpi_type_ids))

    return query.all()
