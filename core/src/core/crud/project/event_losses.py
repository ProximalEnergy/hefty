import datetime

from sqlalchemy.orm import Session

from core import models
from core.model_list import ModelList


def get_event_losses(
    db: Session,
    *,
    time_equals: datetime.datetime | None = None,
    time_gte: datetime.datetime | None = None,
    time_lt: datetime.datetime | None = None,
    event_ids: list | None = None,
    return_query: bool = False,
) -> ModelList[models.EventLoss]:
    query = db.query(models.EventLoss)
    if time_equals is not None:
        query = query.filter(models.EventLoss.time == time_equals)
    if time_gte is not None:
        query = query.filter(models.EventLoss.time >= time_gte)
    if time_lt is not None:
        query = query.filter(models.EventLoss.time < time_lt)
    if event_ids is not None:
        query = query.filter(models.EventLoss.event_id.in_(event_ids))
    return ModelList(query=query, return_query=return_query)
