from sqlalchemy.orm import Session

from core import models
from core.model_list import ModelList


def get_pv_dc_combiners(
    db: Session,
    *,
    return_query: bool = False,
) -> ModelList[models.PVDCCombiner]:
    """TODO: add description.

    Args:
        db: TODO: describe.
        return_query: TODO: describe.
    """
    query = db.query(models.PVDCCombiner)
    return ModelList(query=query, return_query=return_query)
