from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select
from sqlalchemy.orm import noload, selectinload

from core import models


def get_ercot_settlement_point_options(*, deep: bool):
    """Build SQLAlchemy loader options for settlement point queries.

    Args:
        deep: Whether to eager-load related objects.
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


def get_ercot_settlement_points(
    *, deep: bool = False
) -> DbQuery[models.SettlementPoint, Literal[False]]:
    """Build query for ERCOT settlement points.

    Args:
        deep: Whether to eager-load related objects.
    """
    options = get_ercot_settlement_point_options(deep=deep)
    query = select(models.SettlementPoint).options(*options)
    return DbQuery(query=query)
