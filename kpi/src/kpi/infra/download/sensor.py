from datetime import timedelta

import pandas as pd
import polars as pl
from core.crud.operational.sensor_types import get_sensor_types
from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.crud.project.tags import get_project_tags_v2
from core.database import with_db
from core.enumerations import OutputType, SensorTypeEnum, TimeOffset
from kpi.base.exception import NoDownloadedDataError
from kpi.infra.download.async_runner import run_in_loop
from pydantic import ConfigDict, validate_call
from sqlalchemy.orm import Session

from core import models

KPI_TAG_CHUNK_SIZE = 2_000
arbitrary_types = ConfigDict(arbitrary_types_allowed=True)


def _iter_tag_chunks(*, tags: pl.DataFrame) -> list[pl.DataFrame]:
    return [
        tags.slice(i, KPI_TAG_CHUNK_SIZE)
        for i in range(0, len(tags), KPI_TAG_CHUNK_SIZE)
    ]


@validate_call(config=arbitrary_types)
async def async_get_data_timeseries(
    *,
    project_db: Session,
    project_name_short: str,
    tags_chunk: pl.DataFrame,
    start_local: pd.Timestamp,
    end_local: pd.Timestamp,
):
    return await DataTimeseries(
        project_name_short=project_name_short,
        query_start=start_local,
        query_end=end_local + timedelta(minutes=5),
        max_lookback_period=TimeOffset.TWENTY_FOUR_HOURS,
        project_db=project_db,
        filter_method=FilterMethod.TAG_POLARS,
        filter_values=tags_chunk,
        ensure_full_range=True,
        dangerous_pagination_override=False,
    ).get_all()


def sensor_data_df(
    project_name_short: str,
    start_local: pd.Timestamp,
    end_local: pd.Timestamp,
    tags_polars: pl.DataFrame,
):
    with with_db(schema=project_name_short) as project_db:
        data_timeseries_chunks = []
        for tags_chunk in _iter_tag_chunks(tags=tags_polars):
            data_timeseries_chunks.append(
                run_in_loop(
                    async_get_data_timeseries(
                        project_db=project_db,
                        project_name_short=project_name_short,
                        tags_chunk=tags_chunk,
                        start_local=start_local,
                        end_local=end_local,
                    )
                )
            )
    data_raw = pd.concat(
        [
            chunk.df.to_pandas().set_index(models.DataTimeseries.time.name)
            for chunk in data_timeseries_chunks
        ],
        axis=1,
    )
    if data_raw.empty:
        raise NoDownloadedDataError("Dataframe is empty")
    data_raw.index = data_raw.index.tz_convert("UTC").tz_localize(None)
    data_raw.columns = data_raw.columns.astype(int)
    return data_raw


def get_tag_polars(
    *, sensor_type_id_list: list[int], project_name_short: str
) -> pl.DataFrame:
    tags_polars = get_project_tags_v2(
        sensor_type_ids=sensor_type_id_list,
    ).get(
        schema=project_name_short,
        output_type=OutputType.POLARS,
    )
    if tags_polars.is_empty():
        raise NoDownloadedDataError(
            f"No tags found for sensor types {sensor_type_id_list}"
        )
    return tags_polars


def tag_df_from_tags_polars(*, tags: pl.DataFrame) -> pd.DataFrame:
    return (
        tags.select(
            [
                models.Tag.tag_id.name,
                models.Tag.sensor_type_id.name,
                models.Tag.device_id.name,
            ]
        )
        .to_pandas()
        .set_index(models.Tag.tag_id.name)
    )


def get_sensor_types_map(sensor_type_id_list: list[int]) -> dict[int, int]:
    sensor_types = get_sensor_types(
        sensor_type_ids=sensor_type_id_list,
    ).get(schema=None, output_type=OutputType.PANDAS)
    return sensor_types.set_index(models.SensorType.sensor_type_id.name)[
        models.SensorType.device_type_id.name
    ].to_dict()


def get_existing_columns_df(
    tag_df: pd.DataFrame, data_raw: pd.DataFrame, sensor_type: SensorTypeEnum
) -> pd.DataFrame:
    desired_tags = tag_df[tag_df[models.Tag.sensor_type_id.name] == sensor_type.value]
    existing_columns = [
        tag_id for tag_id in desired_tags.index if tag_id in data_raw.columns
    ]
    if len(existing_columns) == 0:
        raise NoDownloadedDataError(
            f"No downloaded tags for sensor type {repr(sensor_type)}"
        )
    filtered_df = data_raw[existing_columns]
    if filtered_df.empty:
        raise NoDownloadedDataError("Filtered dataframe is empty")
    return filtered_df
