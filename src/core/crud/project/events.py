import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, noload, selectinload

from core import models
from core.model_list import ModelList


def get_windowed_events(
    db: Session,
    *,
    start: datetime.datetime,
    end: datetime.datetime,
    deep: bool = False,
    return_query: bool = False,
) -> ModelList[models.Event]:
    """Query events that start before `end` and end after `start` or are ongoing."""
    query = db.query(models.Event)
    query = query.filter(models.Event.time_start <= end)
    query = query.filter(
        or_(models.Event.time_end >= start, models.Event.time_end.is_(None)),
    )
    if deep:
        query = query.options(selectinload(models.Event.device))
    else:
        query = query.options(noload(models.Event.device))
    return ModelList(query=query, return_query=return_query)


def get_maximum_event_id(db: Session) -> int:  # skip-star-syntax
    return db.query(func.max(models.Event.event_id)).scalar() or 0
