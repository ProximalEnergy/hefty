import datetime
from typing import cast

from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.db_query import OutputType
from core.enumerations import SensorType, TimeOffset
from sqlalchemy.orm import Session

import core
from app import utils
from core import models


async def get_bess_data(
    *,
    project: models.Project,
    project_db: Session,
    start: datetime.datetime,
    end: datetime.datetime,
):
    """
    Retrieves BESS data for a given project.

    Args:
        project: The project model.
        project_db: The project database session.
        start: The start datetime for the data query.
        end: The end datetime for the data query.

    Returns:
        A dictionary containing BESS data.
    """
    project_schema = utils.get_project_schema(project_db=project_db)
    tags_df = await core.crud.project.tags.get_project_tags_v2(
        sensor_type_ids=[
            SensorType.BESS_ENCLOSURE_SOC_PERCENT,
            SensorType.BESS_BANK_SOC_PERCENT,
            SensorType.BESS_STRING_SOC_PERCENT,
        ],
        deep=True,
    ).get_async(output_type=OutputType.PANDAS, schema=project_schema)

    if tags_df.empty:
        return {}

    tags_df = tags_df.astype({"tag_id": int, "sensor_type_id": int})

    tag_id_to_device_name_long = (
        tags_df.set_index("tag_id")["device_name_long"].fillna("").to_dict()
    )
    sensor_type_id_to_tag_ids = (
        tags_df.groupby("sensor_type_id")["tag_id"].apply(list).to_dict()
    )

    data = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=tags_df["tag_id"].tolist(),
        query_start=start,
        query_end=end,
        project_db=project_db,
        max_lookback_period=TimeOffset.ONE_HOUR,
    ).get()

    df = data.df.to_pandas().set_index("time")
    df.columns = df.columns.astype(int)

    return_data = {}

    sensor_type_id_to_name = {
        43: "bess_enclosure",
        44: "bess_bank",
        45: "bess_string",
    }

    for sensor_type_id, tag_ids in sensor_type_id_to_tag_ids.items():
        sensor_type_id_int = cast(int, sensor_type_id)
        if sensor_type_id_int:
            sensor_name = sensor_type_id_to_name[sensor_type_id_int]
            return_data[sensor_name] = [
                {
                    "x": df.index.tolist(),
                    "y": df[int(tag_id)].tolist(),
                    "name": tag_id_to_device_name_long[int(tag_id)],
                }
                for tag_id in tag_ids
            ]
            return_data[sensor_name].sort(
                key=lambda x: x["name"],
            )

    return return_data
