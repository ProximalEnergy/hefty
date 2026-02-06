from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import models


async def get_report_types(*, db: AsyncSession):
    """todo

    Args:
        db: Description for db.
    """
    return (await db.execute(select(models.ReportType))).scalars().all()


async def get_report_type(*, db: AsyncSession, report_type_id: int):
    """todo

    Args:
        db: Description for db.
        report_type_id: Description for report_type_id.
    """
    return (
        await db.execute(
            select(models.ReportType).where(
                models.ReportType.report_type_id == report_type_id
            )
        )
    ).scalar_one_or_none()
