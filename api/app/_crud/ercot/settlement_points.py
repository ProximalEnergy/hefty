from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from core import models


def get_ercot_settlement_point_options(*, deep: bool):
    """todo

    Args:
        deep: TODO: describe.
    """
    if deep:
        options = (
            selectinload(models.SettlementPoint.settlement_point_type),
            selectinload(models.SettlementPoint.load_zone),
            selectinload(models.SettlementPoint.trading_hub),
        )
    else:
        options = (
            noload(models.SettlementPoint.settlement_point_type),
            noload(models.SettlementPoint.load_zone),
            noload(models.SettlementPoint.trading_hub),
        )

    return options


async def get_ercot_settlement_points(*, db: AsyncSession, deep: bool = False):
    """todo

    Args:
        db: TODO: describe.
        deep: TODO: describe.
    """
    options = get_ercot_settlement_point_options(deep=deep)
    query = select(models.SettlementPoint).options(*options)
    result = await db.execute(query)
    return result.scalars().all()
