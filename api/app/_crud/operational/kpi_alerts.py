from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_user_kpi_alerts(
    db: AsyncSession,
    *,
    user_id: str,
    project_id: UUID,
    kpi_type_id: int | None = None,
):
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
        project_id: TODO: describe.
        kpi_type_id: TODO: describe.
    """
    query = select(models.KPIAlert)
    query = query.filter(models.KPIAlert.user_id == user_id)
    query = query.filter(models.KPIAlert.project_id == project_id)
    if kpi_type_id is not None:
        query = query.filter(models.KPIAlert.kpi_type_id == kpi_type_id)
    result = await db.execute(query)
    return result.scalars().all()


async def get_user_triggered_alerts(
    db: AsyncSession,
    *,
    user_id: str,
):
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
    """
    query = select(models.KPIAlert)
    query = query.filter(models.KPIAlert.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()


async def trigger_user_alert(
    db: AsyncSession,
    *,
    kpi_alert_id: int,
    triggered: bool,
):
    """todo

    Args:
        db: TODO: describe.
        kpi_alert_id: TODO: describe.
        triggered: TODO: describe.
    """
    query = select(models.KPIAlert)
    query = query.filter(models.KPIAlert.kpi_alert_id == kpi_alert_id)
    result = await db.execute(query)
    kpi_alert = result.scalars().one_or_none()

    if not kpi_alert:
        return None

    config = kpi_alert.config.copy()
    config["triggered"] = triggered
    kpi_alert.config = config

    await db.commit()
    return True


async def add_kpi_alert(
    db: AsyncSession,
    *,
    user_id: str,
    project_id: UUID,
    kpi_type_id: int,
    config: dict,
):
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
        project_id: TODO: describe.
        kpi_type_id: TODO: describe.
        config: TODO: describe.
    """
    db_alert = models.KPIAlert(
        user_id=str(user_id),
        project_id=project_id,
        kpi_type_id=kpi_type_id,
        config=config,
    )
    db.add(db_alert)
    await db.commit()
    return db_alert


async def update_kpi_alert(
    db: AsyncSession,
    *,
    user_id: str,
    project_id: UUID,
    kpi_type_id: int,
    config: dict,
):
    """todo

    Args:
        db: TODO: describe.
        user_id: TODO: describe.
        project_id: TODO: describe.
        kpi_type_id: TODO: describe.
        config: TODO: describe.
    """
    query = select(models.KPIAlert).filter(
        models.KPIAlert.kpi_alert_id == config["kpi_alert_id"]
    )
    result = await db.execute(query)
    db_alert = result.scalars().first()

    if db_alert:
        db_alert.kpi_type_id = kpi_type_id
        for key, value in config.items():
            db_alert.config[key] = value
        new_config = db_alert.config
        await db.execute(
            update(models.KPIAlert)
            .where(models.KPIAlert.kpi_alert_id == config["kpi_alert_id"])
            .values(config=new_config, kpi_type_id=kpi_type_id)
        )
        await db.commit()
        await db.refresh(db_alert)
        return db_alert
    return None


async def delete_kpi_alert(
    db: AsyncSession,
    *,
    alert_id: int,
):
    """todo

    Args:
        db: TODO: describe.
        alert_id: TODO: describe.
    """
    query = select(models.KPIAlert).filter(models.KPIAlert.kpi_alert_id == alert_id)
    result = await db.execute(query)
    db_alert = result.scalars().first()

    if db_alert:
        await db.delete(db_alert)
        await db.commit()
