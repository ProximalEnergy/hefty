import datetime
from collections import defaultdict

from core.crud.project.data_timeseries import DataTimeseries, FilterMethod
from core.enumerations import SensorType, TimeOffset
from sqlalchemy.orm import Session

import core
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
    tags = core.crud.project.tags.get_project_tags(
        project_db,
        sensor_type_ids=[
            SensorType.BESS_ENCLOSURE_SOC_PERCENT,
            SensorType.BESS_BANK_SOC_PERCENT,
            SensorType.BESS_STRING_SOC_PERCENT,
        ],
        deep=True,
    ).models()

    tag_id_to_device_name_long = {t.tag_id: t.device.name_long for t in tags}
    sensor_type_id_to_tag_ids = defaultdict(list)
    for t in tags:
        sensor_type_id_to_tag_ids[t.sensor_type_id].append(t.tag_id)

    data = await DataTimeseries(
        project_name_short=project.name_short,
        filter_method=FilterMethod.TAG_IDS,
        filter_values=[t.tag_id for t in tags],
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
        if sensor_type_id:
            return_data[sensor_type_id_to_name[sensor_type_id]] = [
                {
                    "x": df.index.tolist(),
                    "y": df[tag_id].tolist(),
                    "name": tag_id_to_device_name_long[tag_id],
                }
                for tag_id in tag_ids
            ]
            return_data[sensor_type_id_to_name[sensor_type_id]].sort(
                key=lambda x: x["name"],
            )

    return return_data
