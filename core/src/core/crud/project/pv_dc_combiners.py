from sqlalchemy import select

from core import models
from core.db_query import DbQuery


def get_pv_dc_combiners() -> DbQuery[models.PVDCCombiner]:
    """TODO: add description."""
    stmt = select(models.PVDCCombiner)
    return DbQuery(query=stmt)
