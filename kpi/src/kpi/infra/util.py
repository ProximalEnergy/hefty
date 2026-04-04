import pandas as pd
from core.crud.operational.projects import get_projects
from core.db_query import OutputType

from core import models


def get_project_from_database(name_short: str) -> models.Project:
    query = get_projects(name_short=name_short)
    projects = query.get(output_type=OutputType.SQLALCHEMY)
    if projects is None or len(projects) != 1:
        raise ValueError(
            f"Expected 1 project, got {len(projects) if projects is not None else 0}"
        )
    project = projects[0]
    return project


def index_to_numpy_ns(*, index: pd.Index):
    """Convert index to numpy, coercing datetimes to datetime64[ns].

    Args:
        index: Index to convert.
    """
    if isinstance(index, pd.DatetimeIndex):
        if index.tz is not None:
            return (
                index.tz_convert("UTC")
                .tz_localize(None)
                .to_numpy(dtype="datetime64[ns]")
            )
        return index.to_numpy(dtype="datetime64[ns]")
    return index.to_numpy()


def series_to_numpy_ns(*, series: pd.Series):
    """Convert series to numpy, coercing datetimes to datetime64[ns].

    Args:
        series: Series to convert.
    """
    if isinstance(series.dtype, pd.DatetimeTZDtype):
        return (
            series.dt.tz_convert("UTC")
            .dt.tz_localize(None)
            .to_numpy(dtype="datetime64[ns]")
        )

    if pd.api.types.is_datetime64_any_dtype(series.dtype):
        if isinstance(series.dtype, pd.DatetimeTZDtype):
            series = series.dt.tz_convert("UTC").dt.tz_localize(None)
        return series.to_numpy(dtype="datetime64[ns]")

    return series.to_numpy()
