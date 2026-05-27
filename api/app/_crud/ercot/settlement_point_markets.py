from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_ercot_settlement_point_markets() -> DbQuery[
    models.SettlementPointMarket, Literal[False]
]:
    """Return a query for all ERCOT settlement point markets."""
    query = select(models.SettlementPointMarket)
    return DbQuery(query=query)
