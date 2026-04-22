from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_ercot_qses() -> DbQuery[models.QSE, Literal[False]]:
    """Build a query for all ERCOT QSE records."""
    query = select(models.QSE)
    return DbQuery(query=query)
