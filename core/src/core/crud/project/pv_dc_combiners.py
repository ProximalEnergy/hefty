from typing import Literal

from sqlalchemy import select

from core import models
from core.db_query import DbQuery


def get_pv_dc_combiners() -> DbQuery[models.PVDCCombiner, Literal[False]]:
    """Build a query for PV DC combiner rows."""
    stmt = select(models.PVDCCombiner)
    return DbQuery(query=stmt)
