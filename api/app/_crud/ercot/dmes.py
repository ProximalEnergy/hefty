from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_ercot_dmes() -> DbQuery[models.DME, Literal[False]]:
    """Build a query for all ERCOT DME records."""
    query = select(models.DME)
    return DbQuery(query=query)
