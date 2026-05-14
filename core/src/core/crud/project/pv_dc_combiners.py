from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_pv_dc_combiners() -> DbQuery[models.PVDCCombiner, Literal[False]]:
    """Build a query for PV DC combiner rows."""
    stmt = select(models.PVDCCombiner)
    return DbQuery(query=stmt)
