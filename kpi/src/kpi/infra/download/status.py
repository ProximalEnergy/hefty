from uuid import UUID

import pandas as pd
from core.crud.project.tags import get_project_tags_v2
from core.database import with_db
from core.db_query import OutputType
from core.domain.statuses.statuses import get_status_time_series_failure_mode_ids
from kpi.base.exception import NoDownloadedDataError
from kpi.infra.download.async_runner import run_in_loop
from kpi.infra.util import get_project_by_id

from core import models


def download_status_df(
    project_id: UUID,
    start_tz_aware: pd.Timestamp,
    end_tz_aware: pd.Timestamp,
    sensor_type_ids: list[int],
) -> pd.DataFrame:
    project = get_project_by_id(project_id=project_id)
    with with_db(schema=project.name_short) as project_db:
        data_timeseries = run_in_loop(
            get_status_time_series_failure_mode_ids(
                project_db=project_db,
                start=start_tz_aware,
                end=end_tz_aware,
                project=project,
                sensor_type_ids=sensor_type_ids,
                get_all=True,
            )
        )

    data_raw = pd.DataFrame(data_timeseries)
    if data_raw.empty:
        raise NoDownloadedDataError(
            f"Dataframe is empty for sensor types {sensor_type_ids}"
        )
    data_raw = data_raw.set_index("index")
    if data_raw.empty:
        raise NoDownloadedDataError("Dataframe is empty")
    data_raw.index = data_raw.index.tz_convert("UTC").tz_localize(None)  # type: ignore
    data_raw.columns = data_raw.columns.astype(int)

    # convert to nullable integers
    data_raw = data_raw.astype("Int32")

    return data_raw


def get_tag_df(sensor_type_id_list: list[int], project_name_short: str) -> pd.DataFrame:
    tags = get_project_tags_v2(
        sensor_type_ids=sensor_type_id_list,
    )
    return tags.get(schema=project_name_short, output_type=OutputType.PANDAS).set_index(
        models.Tag.tag_id.name
    )[[models.Tag.sensor_type_id.name, models.Tag.device_id.name]]
