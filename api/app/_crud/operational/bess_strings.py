from typing import Literal

from core.db_query import DbQuery
from sqlalchemy import select

from core import models


def get_bess_strings(
    *,
    bess_string_ids: list[int] | None = None,
    device_model_ids: list[int] | None = None,
) -> DbQuery[models.BESSString, Literal[False]]:
    """Fetch BESS string specifications from operational.bess_strings.

    Args:
        bess_string_ids: Optional BESS string primary keys.
        device_model_ids: Optional device model foreign keys.
    """
    query = select(models.BESSString)

    if bess_string_ids:
        query = query.where(models.BESSString.bess_string_id.in_(bess_string_ids))

    if device_model_ids:
        query = query.where(models.BESSString.device_model_id.in_(device_model_ids))

    return DbQuery(query=query)
