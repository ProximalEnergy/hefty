from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_ercot_settlement_point_types(
    *,
    name_long: str = "",
) -> DbQuery[models.SettlementPointType, Literal[False]]:
    """Build query for ERCOT settlement point types.

    Args:
        name_long: Optional long name filter.
    """
    query = select(models.SettlementPointType)

    if name_long:
        query = query.where(models.SettlementPointType.name_long == name_long)

    return DbQuery(query=query)
