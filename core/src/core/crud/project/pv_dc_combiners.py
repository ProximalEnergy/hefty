from sqlalchemy.orm import Session

from core import models
from core.model_list import ModelList


def get_pv_dc_combiners(
    db: Session,
    *,
    return_query: bool = False,
) -> ModelList[models.PVDCCombiner]:
    query = db.query(models.PVDCCombiner)
    return ModelList(query=query, return_query=return_query)
